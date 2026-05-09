"""
data-collector 全局配置
支持多数据源策略配置、HDFS 路径、日志等
"""

import os
from pathlib import Path

# ============================================================
# 项目路径
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / ".." / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 采集开关 — 可单独启用/禁用某个数据源
# ============================================================
ENABLED_SOURCES = {
    "eastmoney": True,   # 东方财富 (akshare) — A股行情/K线
    "baostock": True,    # Baostock — A股历史K线/基本面（免注册）
    "yahoo": True,       # Yahoo Finance — 港股/美股/全球指数
}

# ============================================================
# 数据源优先级（数字越大优先级越高，多源冲突时使用）
# ============================================================
SOURCE_PRIORITY = {
    "eastmoney": 10,
    "baostock": 8,
    "yahoo": 6,
}

# ============================================================
# 股票代码前缀映射
# ============================================================
STOCK_PREFIX_MAP = {
    # A股
    "6": ".SH",     # 上海主板
    "0": ".SZ",     # 深圳主板
    "3": ".SZ",     # 创业板
    "4": ".BJ",     # 北交所
    "8": ".BJ",
    # 港股
    "hk": ".HK",
    # 美股
    "us": "",
}

# ============================================================
# 默认采集参数
# ============================================================
DEFAULT_KLINE_FREQ = "daily"        # K线频率: daily/weekly/monthly
DEFAULT_KLINE_YEARS = 2             # 默认拉取 2 年历史K线
FUND_NAV_YEARS = 1                  # 基金净值拉取年限
BATCH_SIZE = 100                    # 批量查询时的分批大小
REQUEST_TIMEOUT = 30                # HTTP 请求超时 (秒)
MAX_RETRIES = 3                     # 失败重试次数

# ============================================================
# HDFS 配置（Day 2 T5 阶段使用）
# ============================================================
HDFS = {
    "url": os.getenv("HDFS_URL", "http://localhost:9870"),
    "user": os.getenv("HDFS_USER", "hadoop"),
    "base_path": "/user/hadoop/stock_data",
    "paths": {
        "stock_daily": "/user/hadoop/stock_data/daily",
        "stock_basic": "/user/hadoop/stock_data/basic",
        "fund_nav": "/user/hadoop/stock_data/fund",
    },
}

# ============================================================
# 日志配置
# ============================================================
LOG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": str(PROJECT_ROOT / "logs" / "collector.log"),
    "rotation": "10 MB",
    "retention": "7 days",
}
