"""
数据目录 — 定义所有数据类型及其采集配置

这是全系统的"数据字典"，集中管理：
  - 数据类型标识 (data_type)
  - 适配器采集顺序 (source_order)
  - 存储目标 (MySQL表名 / CSV前缀 / HDFS路径)
  - 业务描述

基于 a-stock-data 的数据分层 + A_system 实际实现整理。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StorageTarget:
    """存储目标配置"""
    mysql_table: Optional[str] = None           # MySQL 表名
    csv_prefix: Optional[str] = None            # CSV 文件名前缀
    hdfs_path: Optional[str] = None             # HDFS 子路径
    retention_days: int = 30                    # 保留天数


@dataclass
class DataTypeDef:
    """数据类型定义"""
    data_type: str                              # 唯一标识
    display_name: str                           # 展示名称
    layer: str                                  # 所属层: market/signal/information
    description: str                            # 描述
    source_order: List[str] = field(default_factory=list)  # 适配器采集顺序
    storage: StorageTarget = field(default_factory=StorageTarget)
    fetch_codes: Optional[List[str]] = None     # 默认采集股票列表
    is_global: bool = False                     # 是否全局数据(不依赖个股)


# ============================================================
# 数据目录（全系统唯一实例）
# ============================================================
DATA_CATALOG: List[DataTypeDef] = [

    # ==================== 行情层 ====================
    DataTypeDef(
        data_type="realtime_quotes",
        display_name="实时行情",
        layer="market",
        description="全市场实时行情+PE/PB/市值/换手率（腾讯财经全市场扫描）",
        source_order=["tencent", "mootdx"],
        storage=StorageTarget(
            mysql_table="stock",
            csv_prefix="realtime_",
            hdfs_path="daily/",
        ),
        is_global=True,             # 腾讯财经支持全市场批量拉取
    ),
    DataTypeDef(
        data_type="history_kline",
        display_name="历史K线",
        layer="market",
        description="全市场日K线（mootdx TCP → 新浪HTTP → 腾讯HTTP，三层故障转移）",
        source_order=["mootdx", "sina_kline"],
        storage=StorageTarget(
            mysql_table="stock_daily",
            csv_prefix="kline_",
            hdfs_path="daily/",
            retention_days=730,
        ),
        # fetch_codes=None — 管道自动迭代全市场股票
    ),
    DataTypeDef(
        data_type="stock_basic",
        display_name="股票基本信息",
        layer="market",
        description="全市场股票基本信息（腾讯财经全市场扫描）",
        source_order=["tencent"],
        storage=StorageTarget(
            mysql_table="stock",
            csv_prefix="stock_basic_",
            hdfs_path="basic/",
        ),
        is_global=True,
    ),

    # ==================== 信号层 ====================
    DataTypeDef(
        data_type="hot_reason",
        display_name="强势股题材归因",
        layer="signal",
        description="当日强势股+题材归因（同花顺）",
        source_order=["ths_hot"],
        storage=StorageTarget(
            mysql_table="signal_hot_reason",
            csv_prefix="hot_reason_",
            hdfs_path="signals/hot_reason/",
        ),
        is_global=True,
    ),
    DataTypeDef(
        data_type="northbound",
        display_name="北向资金",
        layer="signal",
        description="北向资金实时分钟流向（同花顺）",
        source_order=["ths_northbound"],
        storage=StorageTarget(
            mysql_table="signal_northbound",
            csv_prefix="northbound_",
            hdfs_path="signals/northbound/",
        ),
        is_global=True,
    ),
    DataTypeDef(
        data_type="concept_blocks",
        display_name="概念板块归属",
        layer="signal",
        description="全市场行业/概念/地域三维归属（百度PAE，逐只股票迭代）",
        source_order=["baidu"],
        storage=StorageTarget(
            mysql_table="signal_concept_block",
            csv_prefix="concept_blocks_",
            hdfs_path="signals/concept/",
        ),
    ),
    DataTypeDef(
        data_type="fund_flow",
        display_name="个股资金流向",
        layer="signal",
        description="全市场个股资金流向分钟级+20日历史（百度，逐只股票迭代）",
        source_order=["baidu"],
        storage=StorageTarget(
            mysql_table="signal_fund_flow",
            csv_prefix="fund_flow_",
            hdfs_path="signals/fund_flow/",
        ),
    ),
    DataTypeDef(
        data_type="dragon_tiger_daily",
        display_name="全市场龙虎榜",
        layer="signal",
        description="每日全市场龙虎榜（akshare/东财DC）",
        source_order=["akshare_ext"],
        storage=StorageTarget(
            mysql_table="signal_dragon_tiger_detail",
            csv_prefix="dragon_tiger_detail_",
            hdfs_path="signals/dragon_tiger/",
        ),
        is_global=True,
    ),
    DataTypeDef(
        data_type="industry_compare",
        display_name="行业横向对比",
        layer="signal",
        description="同花顺90行业涨跌排名（akshare）",
        source_order=["akshare_ext"],
        storage=StorageTarget(
            mysql_table="signal_daily_industry",
            csv_prefix="industry_compare_",
            hdfs_path="signals/industry/",
        ),
        is_global=True,
    ),
    DataTypeDef(
        data_type="lockup_expiry",
        display_name="限售解禁日历",
        layer="signal",
        description="全市场历史解禁+未来90天预警（akshare，逐只股票迭代）",
        source_order=["akshare_ext"],
        storage=StorageTarget(
            mysql_table="signal_lockup_detail",
            csv_prefix="lockup_",
            hdfs_path="signals/lockup/",
            retention_days=365,
        ),
    ),

    # ==================== 资讯层 ====================
    DataTypeDef(
        data_type="research_reports",
        display_name="研报列表",
        layer="information",
        description="全市场东财研报列表+评级+EPS预测（逐只股票迭代）",
        source_order=["information"],
        storage=StorageTarget(
            mysql_table="info_research_report",
            csv_prefix="research_reports_",
            hdfs_path="info/research/",
            retention_days=365,
        ),
    ),
    DataTypeDef(
        data_type="consensus_eps",
        display_name="机构一致预期EPS",
        layer="information",
        description="全市场同花顺源机构一致预期EPS（逐只股票迭代）",
        source_order=["information"],
        storage=StorageTarget(
            mysql_table="info_consensus_eps",
            csv_prefix="consensus_eps_",
            hdfs_path="info/consensus_eps/",
            retention_days=365,
        ),
    ),
    DataTypeDef(
        data_type="stock_news",
        display_name="个股新闻",
        layer="information",
        description="全市场东财个股新闻（akshare，逐只股票迭代）",
        source_order=["information"],
        storage=StorageTarget(
            mysql_table="info_stock_news",
            csv_prefix="stock_news_",
            hdfs_path="info/stock_news/",
            retention_days=7,
        ),
    ),
    DataTypeDef(
        data_type="cls_news",
        display_name="财联社快讯",
        layer="information",
        description="财联社分钟级电报（akshare）",
        source_order=["information"],
        storage=StorageTarget(
            mysql_table="info_cls_news",
            csv_prefix="cls_news_",
            hdfs_path="info/cls_news/",
            retention_days=3,
        ),
        is_global=True,
    ),
    DataTypeDef(
        data_type="global_news",
        display_name="全球财经资讯",
        layer="information",
        description="东财全球资讯（akshare）",
        source_order=["information"],
        storage=StorageTarget(
            mysql_table="info_global_news",
            csv_prefix="global_news_",
            hdfs_path="info/global_news/",
            retention_days=7,
        ),
        is_global=True,
    ),
    DataTypeDef(
        data_type="filings",
        display_name="巨潮公告",
        layer="information",
        description="全市场沪深北全量公告（akshare/cninfo，逐只股票迭代）",
        source_order=["information"],
        storage=StorageTarget(
            mysql_table="info_filing",
            csv_prefix="filings_",
            hdfs_path="info/filings/",
            retention_days=365,
        ),
    ),
]


def get_data_type_def(data_type: str) -> DataTypeDef:
    """根据数据类型标识获取定义"""
    for d in DATA_CATALOG:
        if d.data_type == data_type:
            return d
    raise KeyError(f"未知数据类型: {data_type}")


def get_types_by_layer(layer: str) -> List[DataTypeDef]:
    """获取指定层的所有数据类型"""
    return [d for d in DATA_CATALOG if d.layer == layer]


def get_types_by_adapter(source_name: str) -> List[DataTypeDef]:
    """获取某个适配器负责的所有数据类型"""
    return [d for d in DATA_CATALOG if source_name in d.source_order]
