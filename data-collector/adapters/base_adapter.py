"""
数据源适配器抽象协议

基于 a-stock-data 项目的多数据源接口分析，设计统一的 DataSourceAdapter 协议：
  - a-stock-data 中每个数据源是独立函数，输入参数不统一，返回类型不统一
  - 本标准适配器强制统一输入(AdapterRequest)和输出(pd.DataFrame)
  - 所有现采集器需包装为 Adapter 实现此协议

适配器生命周期:
  1. 注册: AdapterFactory.register("data_type", [adapter1, adapter2, ...])
  2. 采集: adapter.fetch(request) → pd.DataFrame
  3. 回退: 主适配器失败 → 自动切换到次级适配器
  4. 健康检查: adapter.check_health() → bool
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd


# ============================================================
# 统一请求参数
# ============================================================
@dataclass
class AdapterRequest:
    """适配器统一请求参数

    所有数据源适配器的 fetch() 方法接收此结构，
    内部自行提取需要的字段，忽略不支持的字段。
    这解决了 a-stock-data 各函数参数不一致的问题。
    """
    codes: Optional[List[str]] = None          # 股票代码列表
    code: Optional[str] = None                  # 单股票代码
    start_date: Optional[str] = None            # 起始日期 YYYYMMDD
    end_date: Optional[str] = None              # 结束日期 YYYYMMDD
    date_str: Optional[str] = None              # 单日期 YYYY-MM-DD
    freq: str = "daily"                         # K线频率
    days: int = 30                              # 回溯天数
    top_n: int = 20                             # Top N
    max_pages: int = 5                          # 最大翻页
    extra: Dict[str, Any] = field(default_factory=dict)  # 扩展参数
    fetch_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))


# ============================================================
# 适配器元数据
# ============================================================
@dataclass
class AdapterMetadata:
    """适配器元数据"""
    source_name: str                            # 数据源唯一标识
    priority: int = 0                           # 优先级(数字越大越优先)
    supported_data_types: List[str] = field(default_factory=list)  # 支持的数据类型
    description: str = ""
    avg_latency_ms: float = 0.0
    failure_count: int = 0
    last_success: Optional[datetime] = None


# ============================================================
# 抽象适配器协议
# ============================================================
class DataSourceAdapter(ABC):
    """数据源适配器抽象基类

    所有数据源必须实现此类，归一化到相同的输入/输出协议。
    """

    @property
    @abstractmethod
    def metadata(self) -> AdapterMetadata:
        """适配器元数据"""
        ...

    @abstractmethod
    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        """统一采集入口

        所有适配器接收标准化的 AdapterRequest，
        返回标准化的 pd.DataFrame，列名采用 snake_case。
        不支持的数据类型应返回空的 DataFrame，而非抛异常。
        """
        ...

    @abstractmethod
    def check_health(self) -> bool:
        """健康检查"""
        ...

    def get_supported_types(self) -> List[str]:
        """返回此适配器支持的数据类型列表"""
        return self.metadata.supported_data_types


# ============================================================
# 适配器注册表 & 工厂
# ============================================================
class AdapterRegistry:
    """适配器注册表 — 管理所有适配器和它们的优先级顺序"""

    _adapters: Dict[str, List[DataSourceAdapter]] = {}  # data_type → [适配器列表(按优先级降序)]

    @classmethod
    def register(cls, data_type: str, adapter: DataSourceAdapter):
        """注册适配器到指定数据类型"""
        if data_type not in cls._adapters:
            cls._adapters[data_type] = []
        cls._adapters[data_type].append(adapter)
        # 按优先级降序排列
        cls._adapters[data_type].sort(
            key=lambda a: a.metadata.priority, reverse=True
        )

    @classmethod
    def get_adapters(cls, data_type: str) -> List[DataSourceAdapter]:
        """获取某数据类型的所有适配器（已按优先级排序）"""
        return cls._adapters.get(data_type, [])

    @classmethod
    def get_all_types(cls) -> List[str]:
        """获取所有已注册的数据类型"""
        return list(cls._adapters.keys())

    @classmethod
    def unregister_all(cls):
        """清空注册表（测试用）"""
        cls._adapters.clear()
