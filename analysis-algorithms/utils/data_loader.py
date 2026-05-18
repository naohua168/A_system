"""
数据加载器 — 统一数据源接口

适配新架构（数据采集层 → Kafka → Spark → MySQL/HDFS）：
  - 从 MySQL 读取（存储层）— 主要方式，已处理好的数据
  - 从 HDFS 读取 Parquet（大数据层）— 批量分析
  - 从 data-collector 读取（降级模式）— 当存储层无数据时
  - 从 Redis 读取缓存 — 热数据加速

不再支持：直接调用 StockCrawler 或读取本地 CSV 文件
"""

import sys
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime, timedelta

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def load_csv(filepath: str) -> pd.DataFrame:
    """从 CSV 文件加载K线数据（兼容旧接口 — chanlun/signal.py 等依赖此函数）"""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    rename = {
        "trade_date": "date", "open_price": "open",
        "high_price": "high", "low_price": "low",
        "close_price": "close",
    }
    df = df.rename(columns={c: rename[c] for c in df.columns if c in rename})
    required = ["date", "open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"CSV 缺少必要列: {col}")
    df = df.sort_values("date").reset_index(drop=True)
    return df


class DataLoader:
    """统一数据加载器

    数据源优先级: Redis(缓存) → MySQL(存储层) → HDFS(备份) → Collector(降级)
    """

    def __init__(self, mysql_config: dict = None, redis_host: str = "localhost"):
        self._mysql_conn = None
        self._redis_client = None
        self._hdfs_available = False
        self._redis_host = redis_host

        # 默认 MySQL 配置 — 自动探测可用连接
        self._mysql_config = mysql_config or {
            "host": "localhost", "port": 3306,
            "user": "root", "password": "hadoop123",
            "database": "stock_analysis",
        }

    # ============================
    # MySQL 读取（主要数据源）
    # ============================

    def _get_mysql(self, retry: int = 2):
        """获取 MySQL 连接，支持 Docker 内外两种场景的自动适配"""
        if self._mysql_conn is not None:
            try:
                self._mysql_conn.ping(reconnect=True)
                return self._mysql_conn
            except Exception:
                self._mysql_conn = None

        import pymysql
        # 尝试的连接候选（按优先级）
        candidates = [
            self._mysql_config,                                          # 用户自定义
            {"host": "localhost", "port": 3306, "user": "root",
             "password": "hadoop123", "database": "stock_analysis"},      # 本机直连
            {"host": "host.docker.internal", "port": 3306, "user": "root",
             "password": "hadoop123", "database": "stock_analysis"},      # Docker 容器内连宿主机
            {"host": "mysql", "port": 3306, "user": "root",
             "password": "hadoop123", "database": "stock_analysis"},      # Docker 内网
        ]

        last_error = None
        for cfg in candidates:
            try:
                self._mysql_conn = pymysql.connect(**cfg, charset="utf8mb4",
                                                     connect_timeout=5, read_timeout=10)
                # 更新配置为成功连接的版本
                self._mysql_config = cfg
                return self._mysql_conn
            except Exception as e:
                last_error = e
                continue

        raise ConnectionError(f"MySQL 连接失败（尝试了 {len(candidates)} 个地址）: {last_error}")

    def read_kline(self, code: str, days: int = 365,
                   columns: List[str] = None) -> pd.DataFrame:
        """从 MySQL 读取日K线数据（解析后的标准格式）"""
        conn = self._get_mysql()
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        cols = "*" if not columns else ", ".join(columns)
        sql = f"""
            SELECT {cols} FROM stock_daily
            WHERE stock_code = %s AND trade_date >= %s
            ORDER BY trade_date ASC
        """
        df = pd.read_sql(sql, conn, params=(code, start))

        if df.empty:
            return df

        # 统一列名为标准格式
        rename = {
            "trade_date": "date", "open_price": "open",
            "high_price": "high", "low_price": "low",
            "close_price": "close", "change_percent": "change_pct",
        }
        df = df.rename(columns={c: rename[c] for c in df.columns if c in rename})
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df

    def read_indicators(self, code: str, indicator_type: str = "ma",
                        days: int = 365) -> pd.DataFrame:
        """从 MySQL 读取 Spark 预计算的技术指标"""
        conn = self._get_mysql()
        table_map = {
            "ma": "precomputed_ma",
            "macd": "precomputed_macd",
            "rsi": "precomputed_rsi",
            "bollinger": "precomputed_bollinger",
            "kdj": "precomputed_kdj",
        }
        table = table_map.get(indicator_type)
        if not table:
            raise ValueError(f"不支持的指标类型: {indicator_type}")

        try:
            return pd.read_sql(
                f"SELECT * FROM {table} WHERE stock_code=%s ORDER BY date DESC LIMIT %s",
                conn, params=(code, days),
            )
        except Exception:
            # 表不存在或数据未就绪，返回空
            return pd.DataFrame()

    def read_realtime(self, code: str) -> dict:
        """从 MySQL 读取最新实时行情"""
        df = pd.read_sql(
            "SELECT * FROM stock WHERE stock_code=%s LIMIT 1",
            self._get_mysql(), params=(code,),
        )
        if df.empty:
            return {}
        return df.iloc[-1].to_dict()

    def read_signals(self, code: str, signal_type: str = "hot_reason",
                     days: int = 30) -> pd.DataFrame:
        """从 MySQL 读取信号层数据"""
        conn = self._get_mysql()
        table_map = {
            "hot_reason": "signal_hot_reason",
            "northbound": "signal_northbound",
            "industry": "signal_daily_industry",
            "dragon_tiger": "signal_dragon_tiger_detail",
            "fund_flow": "signal_fund_flow",
            "concept": "signal_concept_block",
            "lockup": "signal_lockup_detail",
        }
        table = table_map.get(signal_type)
        if not table:
            return pd.DataFrame()

        try:
            return pd.read_sql(
                f"SELECT * FROM {table} WHERE stock_code=%s ORDER BY created_at DESC LIMIT %s",
                conn, params=(code, days),
            )
        except Exception:
            return pd.DataFrame()

    # ============================
    # 批量读取（多只股票）
    # ============================

    def read_all_stocks(self) -> pd.DataFrame:
        """读取所有股票基本信息"""
        return pd.read_sql("SELECT * FROM stock", self._get_mysql())

    def read_recent_kline_batch(self, codes: List[str], days: int = 60) -> pd.DataFrame:
        """批量读取多只股票日K线"""
        if not codes:
            return pd.DataFrame()
        placeholders = ",".join(["%s"] * len(codes))
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return pd.read_sql(
            f"""SELECT stock_code as code, trade_date as date,
                       open_price as open, high_price as high,
                       low_price as low, close_price as close,
                       volume, amount
                FROM stock_daily
                WHERE stock_code IN ({placeholders}) AND trade_date >= %s
                ORDER BY trade_date ASC""",
            self._get_mysql(), params=list(codes) + [start],
        )

    # ============================
    # 降级模式（存储层无数据时）
    # ============================

    def read_from_hdfs(self, code: str, data_type: str,
                       date_str: str = None) -> pd.DataFrame:
        """从 HDFS Parquet 读取数据作为灾备"""
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.appName("analysis_loader").getOrCreate()
            base = f"/user/hadoop/stock_data/processed/{data_type}"
            path = f"{base}/{code}/*.parquet" if not date_str else f"{base}/{date_str}/*.parquet"
            df = spark.read.parquet(path)
            return df.toPandas()
        except Exception:
            return pd.DataFrame()

    def read_from_collector(self, code: str, days: int = 365) -> pd.DataFrame:
        """降级模式：直接通过适配器采集（仅调试用）"""
        try:
            from data_collector.pipeline.collection_pipeline import CollectionPipeline
            from data_collector.adapters.collector_adapters import register_all_adapters
            register_all_adapters()
            from data_collector.adapters.base_adapter import AdapterRegistry, AdapterRequest

            adapters = AdapterRegistry.get_adapters("history_kline")
            if not adapters:
                return pd.DataFrame()

            request = AdapterRequest(code=code, days=days)
            df = adapters[0].fetch(request)
            return df
        except Exception:
            return pd.DataFrame()

    def close(self):
        if self._mysql_conn:
            try:
                self._mysql_conn.close()
            except Exception:
                pass


# ============================
# 便捷函数（兼容旧接口）
# ============================

_loader = None


def _get_loader() -> DataLoader:
    global _loader
    if _loader is None:
        _loader = DataLoader()
    return _loader


def load_kline(code: str, days: int = 365) -> pd.DataFrame:
    """便捷函数：加载K线数据（自动选择数据源）"""
    loader = _get_loader()

    # 优先 MySQL
    df = loader.read_kline(code, days)
    if not df.empty:
        return df

    # HDFS 次选
    df = loader.read_from_hdfs(code, "kline")
    if not df.empty:
        return df

    # 最后降级到采集器
    df = loader.read_from_collector(code, days)
    return df


def load_realtime(code: str) -> dict:
    """便捷函数：加载实时行情"""
    return _get_loader().read_realtime(code)


def load_signals(code: str, signal_type: str = "hot_reason") -> pd.DataFrame:
    """便捷函数：加载信号层数据"""
    return _get_loader().read_signals(code, signal_type)


def load_all_stocks() -> pd.DataFrame:
    """便捷函数：加载所有股票"""
    return _get_loader().read_all_stocks()
