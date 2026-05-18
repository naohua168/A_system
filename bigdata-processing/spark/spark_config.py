"""
Spark 共享配置模块 — 统一管理 Spark 会话创建与配置

消除 7 个 batch job 中重复的 create_spark_with_hive() 函数。
统一管理 Hive Metastore、自适应执行、压缩等配置。

用法:
    from spark_config import create_spark_session, SparkConfig

    # 方式1: 快速创建（带 Hive 支持）
    spark = create_spark_session("MyApp")

    # 方式2: 自定义配置
    cfg = SparkConfig(app_name="MyApp").with_hive().with_adaptive().with_parquet()
    spark = cfg.build()
"""

import os
from typing import Optional

from pyspark.sql import SparkSession


# ============================================================
# 默认配置常量
# ============================================================
DEFAULT_HIVE_METASTORE_URIS = os.getenv("HIVE_METASTORE_URIS", "thrift://hive-metastore:9083")
DEFAULT_HIVE_WAREHOUSE_DIR = os.getenv("HIVE_WAREHOUSE_DIR", "/user/hive/warehouse")
DEFAULT_SPARK_MASTER = os.getenv("SPARK_MASTER", "local[2]")

# 输出路径常量（统一管理，避免散落在各 job 中）
OUTPUT_BASE = "/user/hadoop/stock_data/analysis/spark"
OUTPUT_PATHS = {
    "ma_trend": f"{OUTPUT_BASE}/ma_trend",
    "trend_judge": f"{OUTPUT_BASE}/trend_judge",
    "filter_stocks": f"{OUTPUT_BASE}/filter_stocks",
    "correlation": f"{OUTPUT_BASE}/correlation",
    "sector_ranking": f"{OUTPUT_BASE}/sector_ranking",
    "monthly_return": f"{OUTPUT_BASE}/monthly_return",
    "yearly_return": f"{OUTPUT_BASE}/yearly_return",
    "top_gainers": f"{OUTPUT_BASE}/top_gainers",
    "realtime_indicator": f"{OUTPUT_BASE}/indicators",
}


class SparkConfig:
    """Spark 会话配置构建器 — 链式调用"""

    def __init__(self, app_name: str = "StockSparkJob", master: str = DEFAULT_SPARK_MASTER):
        self._builder = SparkSession.builder \
            .appName(app_name) \
            .master(master)
        self._app_name = app_name

    def with_hive(self) -> "SparkConfig":
        """启用 Hive 支持（元数据 + 仓库目录）"""
        self._builder \
            .config("spark.sql.warehouse.dir", DEFAULT_HIVE_WAREHOUSE_DIR) \
            .config("hive.metastore.uris", DEFAULT_HIVE_METASTORE_URIS) \
            .config("spark.sql.catalogImplementation", "hive") \
            .enableHiveSupport()
        return self

    def with_adaptive(self) -> "SparkConfig":
        """启用自适应查询执行 (AQE) — Spark 3.x 性能关键"""
        self._builder \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.adaptive.skewJoin.enabled", "true") \
            .config("spark.sql.adaptive.localShuffleReader.enabled", "true")
        return self

    def with_parquet(self, compression: str = "snappy") -> "SparkConfig":
        """配置 Parquet 压缩"""
        self._builder \
            .config("spark.sql.parquet.compression.codec", compression) \
            .config("spark.sql.parquet.mergeSchema", "false")
        return self

    def with_shuffle_partitions(self, partitions: int = 200) -> "SparkConfig":
        """设置 Shuffle 分区数 — 根据数据量调整"""
        self._builder.config("spark.sql.shuffle.partitions", str(partitions))
        return self

    def with_dynamic_allocation(self) -> "SparkConfig":
        """启用动态资源分配"""
        self._builder \
            .config("spark.dynamicAllocation.enabled", "true") \
            .config("spark.dynamicAllocation.minExecutors", "1") \
            .config("spark.dynamicAllocation.maxExecutors", "10")
        return self

    def with_config(self, key: str, value: str) -> "SparkConfig":
        """添加自定义配置"""
        self._builder.config(key, value)
        return self

    def build(self) -> SparkSession:
        """构建 SparkSession"""
        return self._builder.getOrCreate()


def create_spark_session(
    app_name: str = "StockSparkJob",
    with_hive: bool = True,
    with_adaptive: bool = True,
    master: Optional[str] = None
) -> SparkSession:
    """快速创建标准 Spark 会话

    Args:
        app_name: 应用名称
        with_hive: 是否启用 Hive 支持
        with_adaptive: 是否启用 AQE
        master: Spark Master 地址，默认用环境变量 SPARK_MASTER 或 local[2]

    Returns:
        SparkSession
    """
    cfg = SparkConfig(app_name=app_name, master=master or DEFAULT_SPARK_MASTER)
    if with_hive:
        cfg.with_hive()
    if with_adaptive:
        cfg.with_adaptive()
    cfg.with_parquet()
    return cfg.build()


def save_dataframe(df, path: str, mode: str = "overwrite", partition_cols: list = None):
    """统一保存 DataFrame 到 HDFS Parquet

    Args:
        df: 要保存的 DataFrame
        path: HDFS 输出路径
        mode: 写入模式
        partition_cols: 分区列（可选）

    注意: 为避免 count() 触发额外全表扫描，只记录 path 信息。
          如需行数统计, 请在调用方手动执行。
    """
    writer = df.write.mode(mode).option("compression", "snappy")
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
    writer.parquet(path)
    # 修复: 移除 df.count() 避免额外的全表扫描，仅打印保存路径
    print(f"💾 已保存到: {path}")


def count_and_show(df, label: str = "", limit: int = 20):
    """统一打印 DataFrame 统计信息"""
    total = df.count()
    print(f"\n{'='*55}")
    print(f"📊 {label} — 共 {total} 条记录" if label else f"📊 共 {total} 条记录")
    print(f"{'='*55}")
    df.show(limit, truncate=False)
    return df
