"""Spark MLlib 股票预测原型 — 基于历史数据的简单预测模型

注意：此为学习原型，使用 Spark MLlib 基础 API，用于演示从 Hive 读取数据 -> 特征工程 -> 模型训练 -> 预测的完整流程。
生产环境可使用 XGBoost/LightGBM 等更强大的模型。
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import LinearRegression, RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, TrainValidationSplit
from pyspark.sql.functions import col, lag, round as spark_round
from pyspark.sql.window import Window
from loguru import logger


class StockPredictor:
    """股票预测器 — 基于 Spark MLlib 的简单回归模型"""

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self._model = None
        self._feature_cols = [
            "open", "high", "low", "close", "volume",
            "ma5", "ma10", "ma20",
            "rsi", "macd_dif", "macd_dea",
        ]

    def prepare_features(self, df: DataFrame) -> DataFrame:
        """准备特征数据

        Args:
            df: 包含 open, high, low, close, volume 等列的 DataFrame
        Returns:
            添加了滞后特征和标签的 DataFrame
        """
        w = Window.partitionBy("stock_code").orderBy("trade_date")

        # 添加滞后特征（过去5天的涨跌幅和技术指标）
        for col_name in ["close", "volume", "ma5", "ma10", "ma20"]:
            if col_name in df.columns:
                for i in range(1, 4):
                    df = df.withColumn(f"{col_name}_lag_{i}", lag(col(col_name), i).over(w))

        # 添加标签：次日涨跌幅
        df = df.withColumn("label", spark_round(
            (lag(col("close"), -1).over(w) - col("close")) / col("close") * 100, 4
        ))

        # 过滤空值
        feature_cols = [c for c in df.columns if "_lag_" in c or c in ["open", "high", "low", "volume"]]
        feature_cols = [c for c in feature_cols if c in df.columns]
        return df.dropna(subset=feature_cols + ["label"])

    def train(self, df: DataFrame, model_type: str = "random_forest") -> dict:
        """训练预测模型

        Args:
            df: 特征工程后的 DataFrame
            model_type: "linear" 或 "random_forest"
        Returns:
            训练结果指标
        """
        # 特征向量化
        available_features = [c for c in self._feature_cols if c in df.columns]
        available_features += [c for c in df.columns if "_lag_" in c]

        assembler = VectorAssembler(inputCols=available_features, outputCol="features_unscaled")
        df_vec = assembler.transform(df)

        # 标准化
        scaler = StandardScaler(inputCol="features_unscaled", outputCol="features",
                                withStd=True, withMean=True)
        scaler_model = scaler.fit(df_vec)
        df_scaled = scaler_model.transform(df_vec)

        # 拆分数据集
        train, test = df_scaled.randomSplit([0.8, 0.2], seed=42)

        # 选择模型
        if model_type == "linear":
            base_model = LinearRegression(featuresCol="features", labelCol="label")
        else:
            base_model = RandomForestRegressor(
                featuresCol="features", labelCol="label",
                numTrees=50, maxDepth=10, seed=42,
            )

        # 网格调参
        param_grid = ParamGridBuilder() \
            .addGrid(base_model.regParam if hasattr(base_model, "regParam") else "dummy",
                     [0.01, 0.1]) \
            .build()

        if param_grid and len(param_grid) > 0:
            tvs = TrainValidationSplit(
                estimator=base_model,
                estimatorParamMaps=param_grid,
                evaluator=RegressionEvaluator(labelCol="label", metricName="rmse"),
                trainRatio=0.8,
            )
            self._model = tvs.fit(train)
        else:
            self._model = base_model.fit(train)

        # 评估
        predictions = self._model.transform(test)
        evaluator_rmse = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="rmse")
        evaluator_r2 = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="r2")

        rmse = evaluator_rmse.evaluate(predictions)
        r2 = evaluator_r2.evaluate(predictions)

        logger.info(f"模型训练完成: type={model_type}, RMSE={rmse:.4f}, R2={r2:.4f}")

        return {
            "model_type": model_type,
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "train_count": train.count(),
            "test_count": test.count(),
            "feature_count": len(available_features),
        }

    def predict(self, features: DataFrame) -> DataFrame:
        """对新数据进行预测"""
        if self._model is None:
            raise RuntimeError("模型未训练，请先调用 train()")
        return self._model.transform(features)

    def save(self, path: str):
        """保存模型到指定路径"""
        if self._model is None:
            raise RuntimeError("模型未训练，无法保存")
        # 提取最佳模型（如果使用了交叉验证）
        model = self._model.bestModel if hasattr(self._model, "bestModel") else self._model
        model.write().overwrite().save(path)
        logger.info(f"模型已保存到: {path}")

    def load(self, path: str):
        """加载已训练的模型"""
        from pyspark.ml.regression import RandomForestRegressionModel, LinearRegressionModel
        try:
            self._model = RandomForestRegressionModel.load(path)
        except Exception:
            self._model = LinearRegressionModel.load(path)
        logger.info(f"模型已加载: {path}")


def create_predictor(spark: SparkSession) -> StockPredictor:
    """工厂函数：简化创建预测器"""
    return StockPredictor(spark)
