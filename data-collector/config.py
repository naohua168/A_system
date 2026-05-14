"""
data-collector 全局配置
基于 a-stock-data 项目重构的数据源配置
"""

import os
from pathlib import Path

# ============================================================
# 项目路径
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 采集开关 — 可单独启用/禁用某个数据源
# ============================================================
ENABLED_SOURCES = {
    "mootdx": True,         # 通达信TCP — K线/五档盘口/逐笔成交/财务/F10（需国内IP）
    "tencent": True,        # 腾讯财经 — PE/PB/市值/换手率/涨跌停价（不封IP）
    "ths_hot": True,        # 同花顺热点 — 当日强势股+题材归因（零鉴权73ms）
    "ths_northbound": True, # 同花顺北向 — 北向资金实时分钟流向（零鉴权）
    "baidu": True,          # 百度股市通 — 概念板块+资金流向（PAE协议）
    "akshare_ext": True,    # akshare扩展 — 龙虎榜/解禁/行业/研报/新闻/公告
}

# ============================================================
# 数据源优先级（数字越大优先级越高）
# ============================================================
SOURCE_PRIORITY = {
    "mootdx": 10,           # TCP直连，最稳定，不封IP
    "tencent": 9,           # HTTP，不封IP
    "ths_hot": 8,           # 零鉴权73ms
    "ths_northbound": 8,    # 零鉴权
    "baidu": 7,             # PAE协议
    "akshare_ext": 6,       # akshare，东财源有反爬可能超时
}

# ============================================================
# 股票代码前缀映射（a-stock-data 风格）
# ============================================================
STOCK_PREFIX_MAP = {
    "6": "sh",      # 上海主板
    "9": "sh",      # 科创板
    "0": "sz",      # 深圳主板
    "3": "sz",      # 创业板
    "4": "bj",      # 北交所
    "8": "bj",      # 北交所
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
