"""StockPredictor 单元测试 — 全部 mock，无需真实 pyspark 环境"""
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 完整构建 pyspark module mock 树（覆盖 stock_predictor.py 所有导入）
# ============================================================

def _build_pyspark_mocks():
    """构建完整的 pyspark module mock 树"""
    import unittest.mock as um

    # ── pyspark.sql.functions ──
    F_mod = types.ModuleType("pyspark.sql.functions")
    F_mod.col = um.MagicMock(return_value=um.MagicMock())
    F_mod.lag = um.MagicMock()
    F_mod.round = um.MagicMock()
    F_mod.when = um.MagicMock()
    F_mod.lit = um.MagicMock()
    F_mod.split = um.MagicMock()
    F_mod.regexp_replace = um.MagicMock()
    F_mod.expr = um.MagicMock()
    F_mod.current_timestamp = um.MagicMock()
    F_mod.to_date = um.MagicMock()
    F_mod.size = um.MagicMock()
    F_mod.from_json = um.MagicMock()
    F_mod.explode_outer = um.MagicMock()
    F_mod.array = um.MagicMock()

    # ── pyspark.sql.types ──
    types_mod = types.ModuleType("pyspark.sql.types")
    types_mod.StructType = um.MagicMock()
    types_mod.StructField = um.MagicMock()
    types_mod.StringType = um.MagicMock()
    types_mod.DoubleType = um.MagicMock()
    types_mod.LongType = um.MagicMock()
    types_mod.ArrayType = um.MagicMock()
    types_mod.IntegerType = um.MagicMock()
    types_mod.DecimalType = um.MagicMock()
    types_mod.TimestampType = um.MagicMock()

    # ── pyspark.sql.window ──
    win_mod = types.ModuleType("pyspark.sql.window")
    win_mod.Window = um.MagicMock()
    win_mod.Window.partitionBy.return_value.orderBy.return_value = um.MagicMock()

    # ── pyspark.ml.feature ──
    feat_mod = types.ModuleType("pyspark.ml.feature")
    feat_mod.VectorAssembler = um.MagicMock()
    feat_mod.StandardScaler = um.MagicMock()

    # VectorAssembler(inputCols=..., outputCol=...).transform(df) → mock_df_vec
    _mock_vec = um.MagicMock()
    feat_mod.VectorAssembler.return_value.transform.return_value = _mock_vec

    # StandardScaler(inputCol=..., outputCol=...).fit(df_vec).transform(df_vec) → mock_scaled
    _mock_scaled = um.MagicMock()
    _mock_scaled.randomSplit.return_value = [um.MagicMock(), um.MagicMock()]
    feat_mod.StandardScaler.return_value.fit.return_value.transform.return_value = _mock_scaled

    # TrainValidationSplit.fit(train) → mock_model, 并设置 bestModel
    _mock_trained = um.MagicMock()
    _mock_trained.bestModel = um.MagicMock()

    # ── pyspark.ml.regression ──
    reg_mod = types.ModuleType("pyspark.ml.regression")
    reg_mod.LinearRegression = um.MagicMock()
    reg_mod.RandomForestRegressor = um.MagicMock()
    reg_mod.LinearRegressionModel = um.MagicMock()
    reg_mod.RandomForestRegressionModel = um.MagicMock()
    reg_mod.LinearRegression.return_value.fit.return_value.transform.return_value = um.MagicMock()
    reg_mod.RandomForestRegressor.return_value.fit.return_value.transform.return_value = um.MagicMock()

    # ── pyspark.ml.evaluation ──
    eval_mod = types.ModuleType("pyspark.ml.evaluation")
    eval_mod.RegressionEvaluator = um.MagicMock()
    # 所有 RegressionEvaluator 实例的 evaluate() → float
    eval_mod.RegressionEvaluator.return_value.evaluate.return_value = 0.0

    # ── pyspark.ml.tuning ──
    tune_mod = types.ModuleType("pyspark.ml.tuning")
    tune_mod.ParamGridBuilder = um.MagicMock()
    tune_mod.TrainValidationSplit = um.MagicMock()
    tune_mod.ParamGridBuilder.return_value.addGrid.return_value.build.return_value = [{}]
    # 保存 _mock_trained 用于后续链式调用
    _mock_trained = um.MagicMock()
    _mock_trained.bestModel = um.MagicMock()
    _mock_trained.transform.return_value = um.MagicMock()
    tune_mod.TrainValidationSplit.return_value.fit.return_value = _mock_trained
    reg_mod.LinearRegression.return_value.fit.return_value = _mock_trained
    reg_mod.RandomForestRegressor.return_value.fit.return_value = _mock_trained

    # ── pyspark.ml (parent module) ──
    ml_mod = types.ModuleType("pyspark.ml")
    ml_mod.feature = feat_mod
    ml_mod.regression = reg_mod
    ml_mod.evaluation = eval_mod
    ml_mod.tuning = tune_mod

    # ── pyspark.sql ──
    sql_mod = types.ModuleType("pyspark.sql")
    sql_mod.SparkSession = um.MagicMock()
    sql_mod.DataFrame = um.MagicMock()
    sql_mod.functions = F_mod
    sql_mod.types = types_mod
    sql_mod.Window = win_mod.Window  # 兼容 import

    # ── pyspark (root module) ──
    spark_mod = types.ModuleType("pyspark")
    spark_mod.sql = sql_mod
    spark_mod.ml = ml_mod

    return spark_mod, sql_mod, ml_mod, feat_mod, reg_mod, eval_mod, tune_mod, F_mod, win_mod


# ── 注入所有 mock 模块 ──
_spark, _sql, _ml, _feat, _reg, _eval, _tune, _F, _win = _build_pyspark_mocks()
sys.modules["pyspark"] = _spark
sys.modules["pyspark.sql"] = _sql
sys.modules["pyspark.sql.functions"] = _F
sys.modules["pyspark.sql.types"] = _sql.types
sys.modules["pyspark.sql.window"] = _win
sys.modules["pyspark.ml"] = _ml
sys.modules["pyspark.ml.feature"] = _feat
sys.modules["pyspark.ml.regression"] = _reg
sys.modules["pyspark.ml.evaluation"] = _eval
sys.modules["pyspark.ml.tuning"] = _tune

# 路径设置
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "spark"))

from pyspark.sql import SparkSession, DataFrame


class TestStockPredictorInit:
    """StockPredictor 初始化测试"""

    def test_init_creates_predictor(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)
        assert predictor is not None
        assert predictor._model is None

    def test_init_factory_function(self):
        from spark.mllib.stock_predictor import create_predictor
        spark = SparkSession.builder.getOrCreate()
        predictor = create_predictor(spark)
        assert predictor is not None
        assert hasattr(predictor, "train")
        assert hasattr(predictor, "predict")

    def test_default_feature_cols(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)
        assert "open" in predictor._feature_cols
        assert "close" in predictor._feature_cols
        assert "rsi" in predictor._feature_cols
        assert "macd_dif" in predictor._feature_cols
        assert len(predictor._feature_cols) > 5


class TestStockPredictorPrepareFeatures:
    """特征工程测试"""

    def test_prepare_features_runs(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)

        mock_df = MagicMock()
        mock_df.columns = ["stock_code", "trade_date", "open", "high", "low", "close",
                          "volume", "ma5", "ma10", "ma20", "rsi", "macd_dif", "macd_dea"]
        mock_df.withColumn.return_value = mock_df
        mock_df.dropna.return_value = mock_df

        result = predictor.prepare_features(mock_df)
        assert result is not None
        assert mock_df.withColumn.call_count > 5

    def test_prepare_features_calls_dropna(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)

        mock_df = MagicMock()
        mock_df.columns = ["stock_code", "trade_date", "close", "volume"]
        mock_df.withColumn.return_value = mock_df
        mock_df.dropna.return_value = mock_df

        result = predictor.prepare_features(mock_df)
        mock_df.dropna.assert_called_once()


class TestStockPredictorTrain:
    """模型训练测试"""

    def test_train_linear(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)

        mock_df = MagicMock()
        mock_df.columns = predictor._feature_cols + ["stock_code", "trade_date"]

        result = predictor.train(mock_df, model_type="linear")
        assert result["model_type"] == "linear"
        assert "rmse" in result
        assert "r2" in result

    def test_train_random_forest(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)

        mock_df = MagicMock()
        mock_df.columns = predictor._feature_cols + ["stock_code", "trade_date"]

        result = predictor.train(mock_df, model_type="random_forest")
        assert result["model_type"] == "random_forest"


class TestStockPredictorPredict:
    """预测功能测试"""

    def test_predict_before_train_raises(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)
        with pytest.raises(RuntimeError, match="模型未训练"):
            predictor.predict(MagicMock())

    def test_predict_after_train_returns(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)

        mock_train_df = MagicMock()
        mock_train_df.columns = predictor._feature_cols + ["stock_code", "trade_date"]
        predictor.train(mock_train_df)

        mock_predict_df = MagicMock()
        result = predictor.predict(mock_predict_df)
        assert result is not None


class TestStockPredictorPersistence:
    """模型持久化测试"""

    def test_save_before_train_raises(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)
        with pytest.raises(RuntimeError, match="模型未训练"):
            predictor.save("/tmp/test_model")

    def test_load_with_random_forest(self):
        from spark.mllib.stock_predictor import StockPredictor
        from pyspark.ml.regression import RandomForestRegressionModel
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)
        with patch.object(RandomForestRegressionModel, 'load', return_value=MagicMock()):
            predictor.load("/tmp/test_model")
            assert predictor._model is not None

    def test_save_calls_write(self):
        from spark.mllib.stock_predictor import StockPredictor
        spark = SparkSession.builder.getOrCreate()
        predictor = StockPredictor(spark)

        mock_model = MagicMock()
        mock_model.write.return_value.overwrite.return_value.save.return_value = None
        # MagicMock 自动有 bestModel 属性，会导致走 bestModel 路径
        # 显式设置 bestModel = mock_model 使链式调用一致
        mock_model.bestModel = mock_model
        predictor._model = mock_model

        predictor.save("/tmp/test_model")
        mock_model.write.return_value.overwrite.return_value.save.assert_called_once_with("/tmp/test_model")
