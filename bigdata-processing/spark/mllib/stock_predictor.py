"""Spark MLlib 股票预测引擎 — 增强版

集成:
  1. 特征工程模块 (feature_engineering.py) — 150+ 特征
  2. 模型评估模块 (model_evaluation.py) — 20+ 评估指标
  3. 多模型对比 — 线性回归 vs 随机森林

数据流:
  Hive/MySQL → prepare_features() → 150+ 特征 → train() → evaluate() → predict()
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import LinearRegression, RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, TrainValidationSplit, CrossValidator
from pyspark.sql.functions import col, lag, round as spark_round
from pyspark.sql.window import Window
from loguru import logger

from spark.mllib.feature_engineering import FeatureEngineering, create_feature_engineering
from spark.mllib.model_evaluation import ModelEvaluator, ModelComparator
from spark.spark_config import create_spark_session


class StockPredictor:
    """股票预测器 — 基于 Spark MLlib 的增强回归模型

    用法:
        spark = create_spark_session()
        predictor = StockPredictor(spark)

        # 方式一：端到端训练 + 评估
        result = predictor.train_evaluate(df, model_type="random_forest")

        # 方式二：对比多模型
        comparison = predictor.compare_models(df)

        # 方式三：分步
        df_feat = predictor.prepare_features(df)
        result = predictor.train(df_feat, model_type="random_forest")
        eval_report = predictor.evaluate(test_df)
    """

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self._model = None
        self._model_type = None
        self._feature_cols = []        # 自动检测
        self._scaler_model = None
        self._assembler = None
        self._feature_engineering = FeatureEngineering(spark)
        self._evaluator = ModelEvaluator(spark)

    # ============================================================
    # 特征工程（委托给 FeatureEngineering 模块）
    # ============================================================

    def prepare_features(self, df: DataFrame,
                          with_labels: bool = True,
                          prediction_horizon: int = 5) -> DataFrame:
        """准备特征数据 — 150+ 特征的端到端构建

        Args:
            df: 包含 stock_code, trade_date, open, high, low, close, volume 的 DataFrame
            with_labels: 是否构建预测标签
            prediction_horizon: 预测周期（天）

        Returns:
            特征工程后的完整 DataFrame
        """
        logger.info("[Predictor] 开始特征工程, 输入 %d 行 %d 列",
                     df.count(), len(df.columns))

        result = self._feature_engineering.build_full_features(
            df,
            with_labels=with_labels,
            prediction_horizon=prediction_horizon,
        )

        # 记录可用特征列（排除非特征列）
        self._feature_cols = [
            c for c in result.columns
            if c not in ("stock_code", "trade_date", "label",
                         "label_1d", "label_5d", "label_direction",
                         "features", "features_unscaled", "prediction")
        ]
        logger.info("[Predictor] 特征工程完成: %d 特征", len(self._feature_cols))
        return result

    # ============================================================
    # 特征向量化
    # ============================================================

    def _vectorize(self, df: DataFrame) -> DataFrame:
        """特征向量化 + 标准化"""
        if not self._feature_cols:
            self._feature_cols = [c for c in df.columns
                                  if c not in ("stock_code", "trade_date", "label",
                                               "label_1d", "label_5d", "label_direction",
                                               "features", "features_unscaled", "prediction")]

        self._assembler = VectorAssembler(
            inputCols=self._feature_cols,
            outputCol="features_unscaled",
        )
        df_vec = self._assembler.transform(df)

        scaler = StandardScaler(
            inputCol="features_unscaled",
            outputCol="features",
            withStd=True,
            withMean=True,
        )
        self._scaler_model = scaler.fit(df_vec)
        return self._scaler_model.transform(df_vec)

    # ============================================================
    # 训练
    # ============================================================

    def train(self, df: DataFrame,
              model_type: str = "random_forest",
              label_col: str = "label",
              test_ratio: float = 0.2) -> dict:
        """训练预测模型

        Args:
            df: 特征工程后的 DataFrame（含 label 列）
            model_type: "linear" | "random_forest" | "all"
            test_ratio: 测试集比例

        Returns:
            训练结果指标字典
        """
        logger.info("[Predictor] 开始训练: model=%s, label=%s", model_type, label_col)

        # 向量化
        df_vec = self._vectorize(df)

        # 拆分
        train, test = df_vec.randomSplit([1 - test_ratio, test_ratio], seed=42)
        train_count = train.count()
        test_count = test.count()
        logger.info("[Predictor] 数据拆分: train=%d, test=%d", train_count, test_count)

        # 构建模型
        if model_type == "linear":
            self._model, self._model_type = self._train_linear(train, label_col)
        elif model_type == "random_forest":
            self._model, self._model_type = self._train_random_forest(train, label_col)
        else:
            raise ValueError(f"未知模型类型: {model_type}, 可选: linear/random_forest")

        # 预测 + 评估
        predictions = self._model.transform(test)

        # 使用增强评估
        eval_report = self._evaluator.evaluate_all(
            predictions,
            label_col=label_col,
            model_name=model_type,
        )

        eval_report["train_count"] = train_count
        eval_report["test_count"] = test_count
        eval_report["feature_count"] = len(self._feature_cols)
        eval_report["model_type"] = model_type

        logger.info("[Predictor] 训练完成: R²=%.4f, 方向准确率=%.1f%%",
                     eval_report["regression"]["r2"],
                     eval_report["directional"]["accuracy_pct"])

        # 保存 predictions 供后续分析
        self._last_predictions = predictions
        return eval_report

    def _train_linear(self, train: DataFrame, label_col: str) -> tuple:
        """训练线性回归模型（带网格调参）"""
        lr = LinearRegression(featuresCol="features", labelCol=label_col)

        param_grid = ParamGridBuilder() \
            .addGrid(lr.regParam, [0.01, 0.1, 0.5]) \
            .addGrid(lr.elasticNetParam, [0.0, 0.5, 1.0]) \
            .build()

        tvs = TrainValidationSplit(
            estimator=lr,
            estimatorParamMaps=param_grid,
            evaluator=RegressionEvaluator(labelCol=label_col, metricName="rmse"),
            trainRatio=0.8,
            parallelism=2,
        )
        model = tvs.fit(train)
        return model, "linear_regression"

    def _train_random_forest(self, train: DataFrame, label_col: str) -> tuple:
        """训练随机森林模型（带网格调参）"""
        rf = RandomForestRegressor(
            featuresCol="features",
            labelCol=label_col,
            seed=42,
        )

        param_grid = ParamGridBuilder() \
            .addGrid(rf.numTrees, [30, 50, 100]) \
            .addGrid(rf.maxDepth, [5, 10, 15]) \
            .addGrid(rf.minInstancesPerNode, [2, 5]) \
            .build()

        cv = CrossValidator(
            estimator=rf,
            estimatorParamMaps=param_grid,
            evaluator=RegressionEvaluator(labelCol=label_col, metricName="rmse"),
            numFolds=3,
            parallelism=2,
            seed=42,
        )
        model = cv.fit(train)
        return model, "random_forest"

    # ============================================================
    # 端到端训练 + 评估
    # ============================================================

    def train_evaluate(self, df: DataFrame,
                       model_type: str = "random_forest",
                       prediction_horizon: int = 5) -> dict:
        """端到端训练：特征工程 → 训练 → 评估

        Args:
            df: 原始 K 线数据
            model_type: 模型类型
            prediction_horizon: 预测周期

        Returns:
            评估报告
        """
        df_feat = self.prepare_features(df, prediction_horizon=prediction_horizon)
        report = self.train(df_feat, model_type=model_type)
        return report

    # ============================================================
    # 多模型对比
    # ============================================================

    def compare_models(self, df: DataFrame,
                       prediction_horizon: int = 5) -> dict:
        """对比线性回归和随机森林的性能

        Returns:
            模型对比报告
        """
        df_feat = self.prepare_features(df, prediction_horizon=prediction_horizon)
        comparator = ModelComparator(self.spark)

        for mtype in ["linear", "random_forest"]:
            logger.info("[对比] 训练模型: %s", mtype)

            # 向量化 & 拆分
            df_vec = self._vectorize(df_feat)
            train, test = df_vec.randomSplit([0.8, 0.2], seed=42)
            test_count = test.count()

            if mtype == "linear":
                model, _ = self._train_linear(train, "label")
            else:
                model, _ = self._train_random_forest(train, "label")

            predictions = model.transform(test)
            comparator.add_model(predictions, mtype)

        return comparator.compare()

    # ============================================================
    # 预测 & 序列化
    # ============================================================

    def predict(self, features: DataFrame) -> DataFrame:
        """对新数据进行预测"""
        if self._model is None:
            raise RuntimeError("模型未训练，请先调用 train() 或 train_evaluate()")

        # 确保特征对齐
        df_vec = self._vectorize(features)
        return self._model.transform(df_vec)

    def save(self, path: str):
        """保存模型到指定路径"""
        if self._model is None:
            raise RuntimeError("模型未训练，无法保存")
        model = self._model.bestModel if hasattr(self._model, "bestModel") else self._model
        model.write().overwrite().save(path)
        # 保存特征列名
        import json
        meta_path = path.rstrip("/") + "_metadata.json"
        with open(meta_path, "w") as f:
            json.dump({"feature_cols": self._feature_cols}, f)
        logger.info("[Predictor] 模型已保存: %s (特征=%d)", path, len(self._feature_cols))

    def load(self, path: str):
        """加载已训练的模型"""
        from pyspark.ml.regression import RandomForestRegressionModel, LinearRegressionModel
        import json
        import os

        try:
            self._model = RandomForestRegressionModel.load(path)
            self._model_type = "random_forest"
        except Exception:
            self._model = LinearRegressionModel.load(path)
            self._model_type = "linear_regression"

        # 恢复特征列名
        meta_path = path.rstrip("/") + "_metadata.json"
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
                self._feature_cols = meta.get("feature_cols", [])

        logger.info("[Predictor] 模型已加载: %s", path)
        return self._model

    def get_feature_importance(self) -> list:
        """获取特征重要性（仅随机森林）"""
        if self._model is None:
            return []

        model = self._model.bestModel if hasattr(self._model, "bestModel") else self._model
        if not hasattr(model, "featureImportances"):
            return []

        importances = model.featureImportances.toArray()
        features = sorted(
            zip(self._feature_cols, importances),
            key=lambda x: x[1],
            reverse=True,
        )
        return [{"feature": f, "importance": round(i, 4)} for f, i in features]

    def last_evaluation(self) -> dict:
        """返回最近一次评估报告"""
        return getattr(self, "_last_evaluation", {})


def create_predictor(spark: SparkSession) -> StockPredictor:
    """工厂函数"""
    return StockPredictor(spark)


def run_pipeline(spark: SparkSession = None,
                 source: str = "hive",
                 model_type: str = "random_forest",
                 prediction_horizon: int = 5) -> dict:
    """端到端预测管道 — 从数据源到预测结果

    Args:
        spark: SparkSession, None 时自动创建
        source: "hive" 从 Hive 读取, "mysql" 从 MySQL 读取
        model_type: "linear" | "random_forest" | "all"
        prediction_horizon: 预测周期（天）

    Returns:
        评估报告
    """
    if spark is None:
        spark = create_spark_session(app_name="StockPredictor")

    predictor = create_predictor(spark)

    if source == "hive":
        df = spark.sql("""
            SELECT stock_code, trade_date,
                   open_price AS open, high_price AS high,
                   low_price AS low, close_price AS close,
                   volume, change_percent AS change_pct
            FROM stock_daily
            WHERE trade_date >= date_sub(CURRENT_DATE, 730)
            ORDER BY stock_code, trade_date
        """)
    else:
        raise ValueError(f"未知数据源: {source}, 可选: hive")

    logger.info("[Pipeline] 数据加载完成: %d 行", df.count())

    if model_type == "all":
        report = predictor.compare_models(df, prediction_horizon)
    else:
        report = predictor.train_evaluate(df, model_type, prediction_horizon)

    return report


if __name__ == "__main__":
    """命令行入口: python stock_predictor.py --source hive --model random_forest"""
    import argparse
    parser = argparse.ArgumentParser(description="股票预测管道")
    parser.add_argument("--source", default="hive", choices=["hive"])
    parser.add_argument("--model", default="random_forest",
                        choices=["linear", "random_forest", "all"])
    parser.add_argument("--horizon", type=int, default=5, help="预测周期（天）")
    args = parser.parse_args()

    report = run_pipeline(
        source=args.source,
        model_type=args.model,
        prediction_horizon=args.horizon,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
