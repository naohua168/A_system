"""大数据处理层 Python 单元测试（全部mock，无需真·pyspark环境）"""
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 设置环境变量
os.environ.setdefault("MYSQL_PASSWORD", "hadoop123")

# ============================================================
# Mock pyspark 模块（避免真正的 pyspark 依赖）
# ============================================================
def _create_mock_pyspark():
    """创建完整的 pyspark 模块 mock 树"""
    import unittest.mock as um

    # 创建 pyspark 根模块
    pyspark_mod = types.ModuleType("pyspark")
    pyspark_mod.__path__ = []
    pyspark_mod.__file__ = "<mock pyspark>"

    # pyspark.sql 子模块
    sql_mod = types.ModuleType("pyspark.sql")
    sql_mod.__path__ = []

    # SparkSession mock
    spark_session_cls = um.MagicMock()
    spark_session_cls.builder.return_value.appName.return_value.getOrCreate.return_value = um.MagicMock()

    # DataFrame mock
    DataFrame_cls = um.MagicMock()

    # types/functions
    StructType = um.MagicMock()
    StructField = um.MagicMock()
    StringType = um.MagicMock()
    DoubleType = um.MagicMock()
    LongType = um.MagicMock()
    ArrayType = um.MagicMock()
    IntegerType = um.MagicMock()

    # SQL functions
    F_mod = types.ModuleType("pyspark.sql.functions")
    F_mod.col = um.MagicMock()
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
    F_mod.notna = um.MagicMock()
    F_mod.col.return_value = um.MagicMock()

    # types 模块
    types_mod = types.ModuleType("pyspark.sql.types")
    types_mod.StructType = StructType
    types_mod.StructField = StructField
    types_mod.StringType = StringType
    types_mod.DoubleType = DoubleType
    types_mod.LongType = LongType
    types_mod.ArrayType = ArrayType
    types_mod.IntegerType = IntegerType
    types_mod.DecimalType = um.MagicMock()
    types_mod.TimestampType = um.MagicMock()

    # 挂载子模块
    sql_mod.SparkSession = spark_session_cls
    sql_mod.DataFrame = DataFrame_cls
    sql_mod.functions = F_mod
    sql_mod.types = types_mod

    pyspark_mod.sql = sql_mod

    return pyspark_mod, sql_mod, F_mod, types_mod


# 注入 mock pyspark 到 sys.modules（在真实模块导入前完成）
_pyspark, _sql, _F, _types = _create_mock_pyspark()
sys.modules["pyspark"] = _pyspark
sys.modules["pyspark.sql"] = _sql
sys.modules["pyspark.sql.functions"] = _F
sys.modules["pyspark.sql.types"] = _types

# mock SparkSession.builder 的链式调用
from unittest.mock import MagicMock as _MM
_mock_session = _MM()
_mock_session.builder.appName.return_value.master.return_value.config.return_value.getOrCreate.return_value = _MM()
_sql.SparkSession = _MM(return_value=_mock_session)
_sql.SparkSession.builder = _MM()
_sql.SparkSession.builder.appName.return_value = _MM()
_sql.SparkSession.builder.appName.return_value.master.return_value = _MM()
_sql.SparkSession.builder.appName.return_value.master.return_value.config.return_value = _MM()
_sql.SparkSession.builder.appName.return_value.master.return_value.config.return_value.getOrCreate.return_value = _MM()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# 添加 spark 目录到路径（stream_pipeline 内部依赖 sys.path 动态添加）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "spark"))


class TestSparkConfig:
    """Spark 共享配置模块测试"""

    def test_spark_config_module_exists(self):
        config_path = Path(__file__).resolve().parent.parent / "spark" / "spark_config.py"
        assert config_path.exists()

    def test_output_paths_dict(self):
        from spark.spark_config import OUTPUT_PATHS
        assert "ma_trend" in OUTPUT_PATHS
        assert "correlation" in OUTPUT_PATHS
        assert "yearly_return" in OUTPUT_PATHS
        assert len(OUTPUT_PATHS) >= 8

    def test_spark_config_builder(self):
        from spark.spark_config import SparkConfig
        builder = SparkConfig("test-app", master="local[*]")
        assert builder is not None
        assert builder._app_name == "test-app"


class TestBatchPipeline:
    """批处理管道调度器测试"""

    def test_pipeline_import(self):
        from batch.run_batch_pipeline import BatchPipeline, StepStatus, StepResult
        assert BatchPipeline is not None
        assert StepStatus is not None

    def test_step_status_values(self):
        from batch.run_batch_pipeline import StepStatus
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"

    def test_quality_check_module_exists(self):
        qc_path = Path(__file__).resolve().parent.parent / "batch" / "bigdata_quality.py"
        assert qc_path.exists()

    def test_quality_check_import(self):
        from batch.bigdata_quality import DataQualityChecker
        from unittest.mock import MagicMock
        mock_spark = MagicMock()
        checker = DataQualityChecker(spark=mock_spark)
        assert checker is not None
        assert hasattr(checker, "check_table")


class TestHiveBackup:
    """HDFS 备份恢复测试"""

    def test_backup_config(self):
        from backup.hdfs_backup import MYSQL_CONFIG, BACKUP_TABLES
        assert "host" in MYSQL_CONFIG
        assert "core" in BACKUP_TABLES
        assert "signal" in BACKUP_TABLES
        assert "info" in BACKUP_TABLES

    def test_backup_tables_count(self):
        from backup.hdfs_backup import BACKUP_TABLES
        total_tables = sum(len(g["tables"]) for g in BACKUP_TABLES.values())
        assert total_tables >= 20, f"预期至少20张表, 实际{total_tables}"

    def test_backup_date_columns(self):
        from backup.hdfs_backup import DATE_COLUMN_TABLES
        assert "stock_daily" in DATE_COLUMN_TABLES
        assert "fund_nav" in DATE_COLUMN_TABLES

    def test_restore_module_exists(self):
        restore_path = Path(__file__).resolve().parent.parent / "backup" / "restore_from_backup.py"
        assert restore_path.exists()

    def test_backup_import(self):
        from backup.hdfs_backup import HDFSBackupPipelineV2
        pipeline = HDFSBackupPipelineV2(mode="test")
        assert pipeline is not None
        assert pipeline.mode == "test"
        assert hasattr(pipeline, "run")


class TestStreaming:
    """流处理模块测试"""

    def test_stream_pipeline_exists(self):
        from streaming import stream_pipeline as sp
        assert sp is not None
        assert hasattr(sp, "create_spark")
        assert hasattr(sp, "main")

    def test_stream_pipeline_has_functions(self):
        from streaming import stream_pipeline as sp
        assert hasattr(sp, "parse_realtime_with_df")
        assert hasattr(sp, "parse_kline_with_df")
        assert hasattr(sp, "write_to_mysql")
        assert hasattr(sp, "write_to_hdfs_stream")

    def test_realtime_indicator_exists(self):
        ri_path = Path(__file__).resolve().parent.parent / "spark" / "streaming" / "realtime_indicator.py"
        assert ri_path.exists()

    def test_precompute_indicators_exists(self):
        pp_path = Path(__file__).resolve().parent.parent / "spark" / "batch" / "precompute_indicators.py"
        assert pp_path.exists()
