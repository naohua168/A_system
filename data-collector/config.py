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
    "sina_kline": True,     # 新浪财经 — HTTP K线（全场景可用，mootdx备份）
    "ths_hot": True,        # 同花顺热点 — 当日强势股+题材归因（零鉴权73ms）
    "ths_northbound": True, # 同花顺北向 — 北向资金实时分钟流向（零鉴权）
    "baidu": True,          # 百度股市通 — 概念板块+资金流向（PAE协议）
    "akshare_ext": True,    # akshare扩展 — 龙虎榜/解禁/行业/研报/新闻/公告
    "information": True,    # 资讯层 — 研报+新闻+公告（从 a-stock-data 迁移合并）
}

# ============================================================
# 数据源优先级（数字越大优先级越高）
# ============================================================
SOURCE_PRIORITY = {
    "mootdx": 10,           # TCP直连，最稳定，不封IP
    "sina_kline": 9,        # HTTP新浪K线，全场景可用
    "tencent": 9,           # HTTP，不封IP
    "ths_hot": 8,           # 零鉴权73ms
    "ths_northbound": 8,    # 零鉴权
    "baidu": 7,             # PAE协议
    "akshare_ext": 6,       # akshare，东财源有反爬可能超时
    "information": 5,       # 资讯层，akshare+东财API，有反爬风险
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
KLINE_COLLECT_INTERVAL = 0.3        # K线逐只采集间隔（秒），防止反爬
KLINE_BATCH_SIZE = 50               # K线批量并发采集数
KLINE_RECONNECT_MAX_RETRIES = 5     # K线断线重连最大重试次数
KLINE_AGGREGATE_WEEKLY = True       # 是否聚合周K
KLINE_AGGREGATE_MONTHLY = True      # 是否聚合月K
FUND_NAV_YEARS = 1                  # 基金净值拉取年限
BATCH_SIZE = 100                    # 批量查询时的分批大小
REQUEST_TIMEOUT = 30                # HTTP 请求超时 (秒)
MAX_RETRIES = 3                     # 单次采集失败重试次数
RETRY_BACKOFF_BASE = 1.0           # 指数退避基数字 (秒)
RETRY_BACKOFF_MAX = 30.0           # 指数退避最大间隔 (秒)

# ============================================================
# 熔断器配置
# ============================================================
CIRCUIT_BREAKER = {
    "failure_threshold": 5,          # 连续失败 N 次后熔断
    "recovery_timeout": 60,          # 熔断后等待秒数再尝试恢复
    "half_open_max_attempts": 3,     # 半开状态最大试探次数
}

# ============================================================
# 数据校验配置
# ============================================================
VALIDATION = {
    "price_min": 0.001,              # 价格最小值（合法股票价格 > 0）
    "price_max": 100000,             # 价格最大值
    "volume_min": 0,                 # 成交量最小值（>= 0）
    "change_pct_min": -100,          # 涨跌幅最小值
    "change_pct_max": 100,           # 涨跌幅最大值
    "pe_min": -10000,                # PE 最小值
    "pe_max": 100000,                # PE 最大值
    "date_format": r"^\d{8}$",       # 日期格式 YYYYMMDD
    "nullable_columns": [],          # 允许为空的列
}

# ============================================================
# 数据质量检查配置
# ============================================================
QUALITY_CHECK = {
    "max_null_ratio": 0.5,           # 允许的最大空值比例
    "max_duplicate_ratio": 0.3,      # 允许的最大重复行比例
    "min_rows": 1,                   # 最小有效行数
}

# ============================================================
# 采集器间限流配置
# ============================================================
RATE_LIMIT = {
    "enabled": True,
    "min_interval_between_sources": 0.5,   # 不同数据源采集间的最小间隔 (秒)
    "concept_blocks_interval": 0.3,        # 概念板块API调用间隔 (秒)
    "fund_flow_interval": 0.3,             # 资金流向API调用间隔 (秒)
    "dragon_tiger_interval": 1.0,          # 龙虎榜API调用间隔 (秒)
}

# ============================================================
# MySQL 连接配置（统一管理，消除硬编码）
# 所有模块通过 get_mysql_config() 获取配置
# ============================================================
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "hadoop123"),
    "database": os.getenv("MYSQL_DB", "stock_analysis"),
}

# ============================================================
# Kafka 配置（消除 raw_collector.py 中的硬编码）
# ============================================================
KAFKA_CONFIG = {
    "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "topics": {
        "realtime": "raw_realtime",
        "kline": "raw_kline",
        "fund_nav": "raw_fund_nav",
        "news": "raw_news",
        "filings": "raw_filings",
        "hot_reason": "raw_hot_reason",
        "northbound": "raw_northbound",
        "concept_blocks": "raw_concept_blocks",
        "fund_flow": "raw_fund_flow",
        "dragon_tiger": "raw_dragon_tiger",
    },
    "max_request_size": 10485760,
    "acks": "all",
    "retries": 3,
    "request_timeout_ms": 30000,
}

# ============================================================
# MySQL 同步配置
# ============================================================
MYSQL_SYNC = {
    "batch_size": 200,               # 单批插入行数
    "max_retries": 2,               # 同步失败重试次数
    "reconnect_delay": 3,           # 重连等待秒数
    "connection_timeout": 10,        # 连接超时秒数
}

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
# 资讯层配置（研报 + 新闻 + 公告 — a-stock-data 迁移合并）
# ============================================================
INFORMATION = {
    "research_max_pages": 5,           # 研报列表最大翻页数
    "research_page_size": 100,         # 研报每页条数
    "report_pdf_dir": "./reports",      # 研报PDF下载目录
    "stock_news_days": 30,             # 个股新闻拉取天数
    "max_reports_per_stock": 500,      # 单只股票最大研报缓存数
    "max_news_per_stock": 200,         # 单只股票最大新闻缓存数
}

# ============================================================
# iwencai 语义搜索配置（可选，需免费申请 API Key）
# ============================================================
IWENCAI = {
    "enabled": False,                   # 默认关闭，设置 Key 后自动启用
    "api_key": os.getenv("IWENCAI_API_KEY", ""),
    "base_url": "https://gw.iwencai.com/gateway/darwin/api/v1/search",
    "timeout": 30,
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
