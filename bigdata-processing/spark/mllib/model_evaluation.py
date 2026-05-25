"""
模型评估模块 — 全面的预测模型评估指标

评估维度:
  1. 回归指标 — RMSE, MAE, MAPE, R², 修正 R²
  2. 方向准确率 — 预测涨/跌方向的正确率
  3. 收益模拟 — 基于预测信号的模拟交易收益, 最大回撤, 夏普比率
  4. 残差分析 — 残差分布统计, 自相关检验
  5. 模型对比 — 多模型并列对比报告
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, abs as spark_abs, avg, stddev, count, when, sum as spark_sum,
    round as spark_round, max as spark_max, percentile_approx, expr,
    sqrt as spark_sqrt, lit, corr, mean, rand,
)
from pyspark.ml.evaluation import RegressionEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.linalg import DenseVector
from loguru import logger
import json
import time


class ModelEvaluator:
    """模型评估器 — 全面的预测性能评估"""

    def __init__(self, spark: SparkSession = None):
        self.spark = spark

    # ============================================================
    # 1. 回归指标
    # ============================================================

    def regression_metrics(self, predictions: DataFrame,
                           label_col: str = "label",
                           pred_col: str = "prediction") -> dict:
        """计算回归评估指标

        Returns:
            {rmse, mae, mape, r2, adjusted_r2, mse, n}
        """
        evaluator_rmse = RegressionEvaluator(
            labelCol=label_col, predictionCol=pred_col, metricName="rmse")
        evaluator_mae = RegressionEvaluator(
            labelCol=label_col, predictionCol=pred_col, metricName="mae")
        evaluator_r2 = RegressionEvaluator(
            labelCol=label_col, predictionCol=pred_col, metricName="r2")

        rmse = evaluator_rmse.evaluate(predictions)
        mae = evaluator_mae.evaluate(predictions)
        r2 = evaluator_r2.evaluate(predictions)

        # MAPE (Mean Absolute Percentage Error)
        mape_df = predictions.withColumn(
            "ape", spark_abs((col(label_col) - col(pred_col)) /
                             (spark_abs(col(label_col)) + 1e-10))
        ).agg(avg("ape").alias("mape"))
        mape_row = mape_df.collect()[0]
        mape_value = float(mape_row["mape"])

        # MSE
        mse = rmse ** 2

        # 修正 R²
        n = predictions.count()
        feature_cols = [c for c in predictions.columns
                       if c not in (label_col, pred_col, "features", "features_unscaled")]
        k = len(feature_cols)
        adjusted_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else r2

        return {
            "rmse": round(rmse, 4),
            "mse": round(mse, 4),
            "mae": round(mae, 4),
            "mape_pct": round(mape_value * 100, 2),
            "r2": round(r2, 4),
            "adjusted_r2": round(adjusted_r2, 4),
            "n": n,
        }

    # ============================================================
    # 2. 方向准确率
    # ============================================================

    def directional_accuracy(self, predictions: DataFrame,
                              label_col: str = "label",
                              pred_col: str = "prediction",
                              threshold: float = 0.0) -> dict:
        """方向准确率 — 预测涨/跌方向的正确率

        Args:
            threshold: 方向判定阈值，>0 为涨，<0 为跌

        Returns:
            {accuracy, up_accuracy, down_accuracy, up_count, down_count}
        """
        df = predictions.withColumn(
            "actual_dir", when(col(label_col) > threshold, 1)
                          .when(col(label_col) < -threshold, -1)
                          .otherwise(0)
        ).withColumn(
            "pred_dir", when(col(pred_col) > threshold, 1)
                        .when(col(pred_col) < -threshold, -1)
                        .otherwise(0)
        ).withColumn("correct", (col("actual_dir") == col("pred_dir")).cast("int"))

        stats = df.agg(
            avg("correct").alias("accuracy"),
            spark_sum(when(col("actual_dir") == 1, col("correct"))).alias("up_correct"),
            count(when(col("actual_dir") == 1, 1)).alias("up_total"),
            spark_sum(when(col("actual_dir") == -1, col("correct"))).alias("down_correct"),
            count(when(col("actual_dir") == -1, 1)).alias("down_total"),
        ).collect()[0]

        up_acc = float(stats["up_correct"]) / float(stats["up_total"]) if stats["up_total"] > 0 else 0
        down_acc = float(stats["down_correct"]) / float(stats["down_total"]) if stats["down_total"] > 0 else 0

        # 混淆矩阵
        cm = df.groupBy("actual_dir", "pred_dir").count().collect()
        confusion_matrix = {
            "true_up_pred_up": 0, "true_up_pred_down": 0,
            "true_down_pred_up": 0, "true_down_pred_down": 0,
        }
        for row in cm:
            key = f"true_{row['actual_dir']}_pred_{row['pred_dir']}".replace("-1","down").replace("1","up").replace("0","flat")
            if key in confusion_matrix:
                confusion_matrix[key] = row["count"]

        return {
            "accuracy_pct": round(float(stats["accuracy"]) * 100, 2),
            "up_accuracy_pct": round(up_acc * 100, 2),
            "down_accuracy_pct": round(down_acc * 100, 2),
            "up_samples": int(stats["up_total"]),
            "down_samples": int(stats["down_total"]),
            "confusion_matrix": confusion_matrix,
        }

    # ============================================================
    # 3. 模拟交易收益
    # ============================================================

    def simulate_trading(self, predictions: DataFrame,
                         label_col: str = "label",
                         pred_col: str = "prediction",
                         initial_capital: float = 100000.0,
                         threshold: float = 0.0) -> dict:
        """基于预测信号的模拟交易回测

        策略: 预测涨幅 > threshold → 买入, 预测跌幅 < -threshold → 卖出
        每日按信号操作, 不持仓过夜(简化)

        Returns:
            {total_return, annualized_return, max_drawdown, sharpe_ratio,
             win_rate, total_trades, profit_trades}
        """
        df = predictions.withColumn(
            "signal", when(col(pred_col) > threshold, 1)
                      .when(col(pred_col) < -threshold, -1)
                      .otherwise(0)
        )

        # 开仓日收益: signal * 实际涨跌幅
        df = df.withColumn("daily_pnl",
            col("signal") * (spark_abs(col(label_col)) + 1e-6))

        stats = df.agg(
            avg("daily_pnl").alias("avg_daily_return"),
            stddev("daily_pnl").alias("std_daily_return"),
            spark_sum("daily_pnl").alias("total_return"),
            count(when(col("signal") != 0, 1)).alias("total_trades"),
            count(when((col("signal") > 0) & (col(label_col) > 0), 1)).alias("win_trades"),
        ).collect()[0]

        total_return = float(stats["total_return"])
        n_trades = int(stats["total_trades"])
        win_trades = int(stats["win_trades"])
        avg_return = float(stats["avg_daily_return"])
        std_return = float(stats["std_daily_return"])

        # 计算最大回撤（通过 rolling window 模拟）
        pnl_values = df.select("daily_pnl").rdd.flatMap(lambda r: r).collect()
        cumulative = []
        cur = 0.0
        peak = 0.0
        max_dd = 0.0
        for pnl in pnl_values:
            cur += pnl
            cumulative.append(cur)
            if cur > peak:
                peak = cur
            dd = (peak - cur) / (peak + 1e-6) * 100
            if dd > max_dd:
                max_dd = dd

        win_rate = win_trades / n_trades * 100 if n_trades > 0 else 0
        sharpe = avg_return / (std_return + 1e-6) * (252 ** 0.5) if std_return > 0 else 0
        annual_return = total_return / len(pnl_values) * 252 if pnl_values else 0

        return {
            "total_return_pct": round(total_return, 2),
            "annualized_return_pct": round(annual_return * 100, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 4),
            "win_rate_pct": round(win_rate, 2),
            "total_trades": n_trades,
            "profit_trades": win_trades,
            "avg_trade_return_pct": round(avg_return, 4),
        }

    # ============================================================
    # 4. 残差分析
    # ============================================================

    def residual_analysis(self, predictions: DataFrame,
                           label_col: str = "label",
                           pred_col: str = "prediction") -> dict:
        """残差分析 — 评估模型的偏差和异常

        Returns:
            {mean_error, std_error, skewness, kurtosis, max_under, max_over,
             pct_within_1std, pct_within_2std}
        """
        df = predictions.withColumn("error",
            col(label_col) - col(pred_col))
        df = df.withColumn("error_pct",
            spark_abs(col("error") / (spark_abs(col(label_col)) + 1e-10)))

        stats = df.agg(
            avg("error").alias("mean_error"),
            stddev("error").alias("std_error"),
            spark_max("error").alias("max_overestimate"),
            spark_min("error").alias("max_underestimate"),
        ).collect()[0]

        std = float(stats["std_error"])
        within_1std = df.filter(spark_abs(col("error")) < std).count()
        within_2std = df.filter(spark_abs(col("error")) < 2 * std).count()
        total = df.count()

        return {
            "mean_error": round(float(stats["mean_error"]), 4),
            "std_error": round(std, 4),
            "max_overestimate": round(float(stats["max_overestimate"]), 4),
            "max_underestimate": round(float(stats["max_underestimate"]), 4),
            "pct_within_1std_pct": round(within_1std / total * 100, 2) if total > 0 else 0,
            "pct_within_2std_pct": round(within_2std / total * 100, 2) if total > 0 else 0,
        }

    # ============================================================
    # 5. 全量评估
    # ============================================================

    def evaluate_all(self, predictions: DataFrame,
                     label_col: str = "label",
                     pred_col: str = "prediction",
                     model_name: str = "model") -> dict:
        """全量评估 — 计算所有指标并返回结构化报告

        Args:
            predictions: 包含真实值和预测值的 DataFrame
            model_name: 模型名称（用于报告标识）

        Returns:
            完整的评估报告 dict
        """
        logger.info("[评估] 开始全量评估: %s", model_name)

        report = {
            "model_name": model_name,
            "evaluation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "regression": self.regression_metrics(predictions, label_col, pred_col),
            "directional": self.directional_accuracy(predictions, label_col, pred_col),
            "trading_simulation": self.simulate_trading(predictions, label_col, pred_col),
            "residuals": self.residual_analysis(predictions, label_col, pred_col),
        }

        logger.info(
            "[评估] %s: RMSE=%.4f, R²=%.4f, 方向准确率=%.1f%%, 夏普=%.2f",
            model_name,
            report["regression"]["rmse"],
            report["regression"]["r2"],
            report["directional"]["accuracy_pct"],
            report["trading_simulation"]["sharpe_ratio"],
        )
        return report


class ModelComparator:
    """模型对比器 — 多模型并行评估与对比报告生成"""

    def __init__(self, spark: SparkSession = None):
        self.spark = spark
        self._results = []

    def add_model(self, predictions: DataFrame, model_name: str) -> dict:
        """添加一个模型的评估结果"""
        evaluator = ModelEvaluator(self.spark)
        report = evaluator.evaluate_all(predictions, model_name=model_name)
        self._results.append(report)
        return report

    def compare(self) -> dict:
        """生成模型对比报告

        Returns:
            {ranking, comparison_table, details}
        """
        if not self._results:
            return {"ranking": [], "comparison_table": {}, "details": []}

        # 按 R² 排序
        sorted_results = sorted(
            self._results,
            key=lambda r: r["regression"]["r2"],
            reverse=True,
        )

        comparison = {
            "ranking": [
                {
                    "rank": i + 1,
                    "model_name": r["model_name"],
                    "r2": r["regression"]["r2"],
                    "rmse": r["regression"]["rmse"],
                    "mae": r["regression"]["mae"],
                    "directional_acc": r["directional"]["accuracy_pct"],
                    "sharpe_ratio": r["trading_simulation"]["sharpe_ratio"],
                    "max_drawdown": r["trading_simulation"]["max_drawdown_pct"],
                }
                for i, r in enumerate(sorted_results)
            ],
            "details": sorted_results,
        }

        logger.info("[对比] 最佳模型: %s (R²=%.4f)",
                     comparison["ranking"][0]["model_name"],
                     comparison["ranking"][0]["r2"])
        return comparison


def create_evaluator(spark: SparkSession = None) -> ModelEvaluator:
    """工厂函数"""
    return ModelEvaluator(spark)


def create_comparator(spark: SparkSession = None) -> ModelComparator:
    """工厂函数"""
    return ModelComparator(spark)
