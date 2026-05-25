"""
特征工程模块 — 为股票预测提供全面的特征构建与筛选

特征分类:
  1. 基础行情特征 — OHLCV, 涨跌幅, 换手率
  2. 技术指标特征 — MA, MACD, RSI, KDJ, BOLL, ATR
  3. 统计特征 — 滚动均值/标准差/偏度/峰度, 相关系数
  4. 滞后特征 — 过去 N 天的各类特征值
  5. 时间特征 — 星期几, 月份, 季度, 年内第几天
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, lag, lit, when, round as spark_round, sqrt as spark_sqrt,
    abs as spark_abs, avg, stddev, skewness, kurtosis, corr,
    dayofweek, month, quarter, dayofyear, weekofyear, year,
    count, min as spark_min, max as spark_max, row_number,
    expr, array, struct, coalesce, log as spark_log,
)
from pyspark.sql.types import DoubleType
from pyspark.sql.window import Window
from loguru import logger


class FeatureEngineering:
    """特征工程处理器 — 从原始 K 线数据构建 ML 特征集"""

    def __init__(self, spark: SparkSession = None):
        self.spark = spark
        self._feature_metadata = {}  # 记录每个特征的创建来源

    # ============================================================
    # 1. 基础衍生特征
    # ============================================================

    def add_price_patterns(self, df: DataFrame) -> DataFrame:
        """价格形态特征 — 反映日内/日间价格结构"""
        w = Window.partitionBy("stock_code").orderBy("trade_date")

        # 涨跌幅
        if "change_pct" not in df.columns:
            df = df.withColumn("change_pct", spark_round(
                (col("close") - col("pre_close")) / col("pre_close") * 100, 4
            ))

        # 振幅
        df = df.withColumn("amplitude", spark_round(
            (col("high") - col("low")) / coalesce(col("pre_close"), col("close")) * 100, 4
        ))

        # 上下影线比例
        df = df.withColumn("upper_shadow", spark_round(
            (col("high") - spark_max(col("open"), col("close"))) / (col("high") - col("low") + 1e-10), 4
        ))
        df = df.withColumn("lower_shadow", spark_round(
            (spark_min(col("open"), col("close")) - col("low")) / (col("high") - col("low") + 1e-10), 4
        ))

        # 实体占比（阳线/阴线实体占振幅比例）
        df = df.withColumn("body_pct", spark_round(
            spark_abs(col("close") - col("open")) / (col("high") - col("low") + 1e-10), 4
        ))

        # 价格位置（收盘价在当日区间中的相对位置）
        df = df.withColumn("price_position", spark_round(
            (col("close") - col("low")) / (col("high") - col("low") + 1e-10), 4
        ))

        # 连续涨跌天数
        df = df.withColumn("is_up", (col("close") > col("pre_close")).cast("int"))
        df = df.withColumn("consecutive_up",
            when(col("is_up") == 1, coalesce(lag("consecutive_up", 1).over(w), lit(0)) + 1).otherwise(0))
        df = df.withColumn("consecutive_down",
            when(col("is_up") == 0, coalesce(lag("consecutive_down", 1).over(w), lit(0)) + 1).otherwise(0))

        logger.debug("[FE] 价格形态特征已添加: amplitude, upper/lower_shadow, body_pct, price_position, consecutive")
        return df

    def add_volatility_features(self, df: DataFrame,
                                 windows: list = None) -> DataFrame:
        """波动率特征 — 滚动窗口标准差/ATR/波动率比"""
        windows = windows or [5, 10, 20]
        w = Window.partitionBy("stock_code").orderBy("trade_date")

        for period in windows:
            w_rows = w.rowsBetween(-period + 1, 0)

            # 波动率（收益率标准差）
            df = df.withColumn(f"volatility_{period}",
                spark_round(stddev("change_pct").over(w_rows), 4))

            # ATR (Average True Range)
            df = df.withColumn(f"atr_{period}",
                spark_round(avg(spark_max(
                    col("high") - col("low"),
                    spark_abs(col("high") - col("pre_close")),
                    spark_abs(col("low") - col("pre_close")),
                )).over(w_rows), 4))

            # 价格归一化波动率
            df = df.withColumn(f"norm_vol_{period}",
                spark_round(stddev("change_pct").over(w_rows) /
                           (avg("change_pct").over(w_rows) + 1e-10), 4))

        # 波动率比值（短期/长期）
        if 5 in windows and 20 in windows:
            df = df.withColumn("vol_ratio_5_20",
                spark_round(col("volatility_5") / (col("volatility_20") + 1e-10), 4))

        logger.debug("[FE] 波动率特征已添加")
        return df

    def add_rolling_stats(self, df: DataFrame, windows: list = None) -> DataFrame:
        """滚动统计特征 — 均值/最大回撤/成交量变化"""
        windows = windows or [5, 10, 20, 60]
        w = Window.partitionBy("stock_code").orderBy("trade_date")

        for period in windows:
            w_rows = w.rowsBetween(-period + 1, 0)

            # 滚动均价
            df = df.withColumn(f"sma_{period}",
                spark_round(avg("close").over(w_rows), 2))

            # 滚动最高/最低
            df = df.withColumn(f"hh_{period}", spark_max("high").over(w_rows))
            df = df.withColumn(f"ll_{period}", spark_min("low").over(w_rows))

            # 当前价格在滚动区间内的位置 (0~1)
            df = df.withColumn(f"percentile_{period}", spark_round(
                (col("close") - col(f"ll_{period}")) /
                (col(f"hh_{period}") - col(f"ll_{period}") + 1e-10), 4
            ))

            # 成交量相对均值
            df = df.withColumn(f"volume_ratio_{period}", spark_round(
                col("volume") / (avg("volume").over(w_rows) + 1e-10), 4
            ))

            # 滚动偏度 & 峰度
            df = df.withColumn(f"skew_{period}",
                spark_round(skewness("change_pct").over(w_rows), 4))
            df = df.withColumn(f"kurt_{period}",
                spark_round(kurtosis("change_pct").over(w_rows), 4))

        logger.debug("[FE] 滚动统计特征已添加")
        return df

    def add_lag_features(self, df: DataFrame,
                          base_cols: list = None,
                          lags: list = None) -> DataFrame:
        """滞后特征 — 过去 N 天的各类特征值

        Args:
            base_cols: 要生成滞后特征的列名列表
            lags: 滞后天数列表

        Returns:
            添加了 lag 列的 DataFrame
        """
        base_cols = base_cols or [
            "close", "volume", "change_pct", "amplitude",
            "ma5", "ma10", "rsi", "macd_dif",
        ]
        lags = lags or [1, 2, 3, 5, 10]
        w = Window.partitionBy("stock_code").orderBy("trade_date")

        for col_name in base_cols:
            if col_name not in df.columns:
                continue
            for lag_n in lags:
                df = df.withColumn(f"{col_name}_lag_{lag_n}",
                    lag(col(col_name), lag_n).over(w))

        logger.debug("[FE] 滞后特征已添加: %d features", len(base_cols) * len(lags))
        return df

    def add_time_features(self, df: DataFrame) -> DataFrame:
        """时间特征 — 周期性编码"""
        if "trade_date" not in df.columns:
            return df

        df = df.withColumn("dow", dayofweek("trade_date"))       # 星期几 1-7
        df = df.withColumn("month", month("trade_date"))          # 月份 1-12
        df = df.withColumn("quarter", quarter("trade_date"))      # 季度 1-4
        df = df.withColumn("doy", dayofyear("trade_date"))        # 年内第几天
        df = df.withColumn("woy", weekofyear("trade_date"))       # 年内第几周

        # 周期性编码 (sin/cos)
        df = df.withColumn("dow_sin", expr(f"sin(2 * pi() * dow / 7)"))
        df = df.withColumn("dow_cos", expr(f"cos(2 * pi() * dow / 7)"))
        df = df.withColumn("month_sin", expr(f"sin(2 * pi() * month / 12)"))
        df = df.withColumn("month_cos", expr(f"cos(2 * pi() * month / 12)"))

        logger.debug("[FE] 时间特征已添加")
        return df

    def add_cross_features(self, df: DataFrame) -> DataFrame:
        """交叉特征 — 特征间组合"""
        # 价格 × 成交量关系
        if "close" in df.columns and "volume_ratio_5" in df.columns:
            df = df.withColumn("price_volume_divergence",
                spark_round(col("change_pct") * col("volume_ratio_5"), 4))

        # 波动率 × 成交量
        if "volatility_5" in df.columns and "volume_ratio_5" in df.columns:
            df = df.withColumn("vol_volume_cross",
                spark_round(col("volatility_5") * col("volume_ratio_5"), 4))

        logger.debug("[FE] 交叉特征已添加")
        return df

    # ============================================================
    # 标签构建
    # ============================================================

    def add_labels(self, df: DataFrame,
                   horizons: list = None) -> DataFrame:
        """构建预测标签（未来收益率）

        Args:
            horizons: 预测周期列表，如 [1, 3, 5] 表示未来1/3/5天收益率

        Returns:
            添加了 label_1/3/5 列的 DataFrame
        """
        horizons = horizons or [1, 5]
        w = Window.partitionBy("stock_code").orderBy("trade_date")

        for h in horizons:
            df = df.withColumn(f"label_{h}d", spark_round(
                (lead("close", h).over(w) - col("close")) / col("close") * 100, 4
            ))

        # 默认标签 = 未来 5 天收益率
        if "label" not in df.columns:
            df = df.withColumn("label", col("label_5d"))

        # 方向标签（分类可用）
        df = df.withColumn("label_direction",
            when(col("label") > 0.5, lit(2))     # 明显上涨
            .when(col("label") < -0.5, lit(0))   # 明显下跌
            .otherwise(lit(1)))                   # 震荡

        logger.debug("[FE] 标签已构建: %s", horizons)
        return df

    # ============================================================
    # 全流程
    # ============================================================

    def build_full_features(self, df: DataFrame,
                            with_labels: bool = True,
                            prediction_horizon: int = 5) -> DataFrame:
        """端到端特征构建 — 从原始 K 线到完整特征集

        Args:
            df: 包含 stock_code, trade_date, open, high, low, close, volume, pre_close 的 DataFrame
            with_labels: 是否构建预测标签
            prediction_horizon: 预测周期（天）

        Returns:
            构建完成的特征 DataFrame
        """
        logger.info("[FE] 开始端到端特征构建, 输入: %d 行", df.count())

        df = self.add_price_patterns(df)
        df = self.add_volatility_features(df)
        df = self.add_rolling_stats(df)
        df = self.add_time_features(df)
        df = self.add_cross_features(df)

        # 滞后特征（最后执行，确保包含了所有新列）
        new_cols = [c for c in df.columns
                    if c not in ("stock_code", "trade_date", "open", "high",
                                 "low", "close", "volume", "pre_close")]
        df = self.add_lag_features(df, base_cols=["close", "volume", "change_pct",
                                                   "amplitude", "volatility_5"])

        if with_labels:
            df = self.add_labels(df, horizons=[prediction_horizon])

        # 过滤空值
        feature_cols = [c for c in df.columns
                        if c not in ("stock_code", "trade_date")]
        before = df.count()
        df = df.dropna(subset=feature_cols)
        after = df.count()

        logger.info("[FE] 特征构建完成: %d 特征, %d → %d 行 (过滤 %d 行空值)",
                     len([c for c in df.columns if c != "stock_code" and c != "trade_date"]),
                     before, after, before - after)
        return df


def create_feature_engineering(spark: SparkSession = None) -> FeatureEngineering:
    """工厂函数"""
    return FeatureEngineering(spark)


def lead(col_name: str, offset: int):
    """pyspark.sql.functions 没有 lead，用 expr 替代"""
    from pyspark.sql.functions import expr
    return expr(f"lead({col_name}, {offset}) OVER (PARTITION BY stock_code ORDER BY trade_date)")
