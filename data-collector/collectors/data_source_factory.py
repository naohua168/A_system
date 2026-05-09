"""
DataSourceFactory — 数据源工厂
根据配置自动选择/组合数据源，支持故障转移
"""

from typing import Dict, List, Optional

import pandas as pd

from .base_collector import BaseCollector
from .eastmoney_collector import EastMoneyCollector
from .baostock_collector import BaoStockCollector
from .yahoo_collector import YahooCollector


# 采集器注册表 — 新增数据源只需在这里注册
_COLLECTOR_REGISTRY: Dict[str, type] = {
    "eastmoney": EastMoneyCollector,
    "baostock": BaoStockCollector,
    "yahoo": YahooCollector,
}


class DataSourceFactory:
    """数据源工厂 — 工厂模式 + 策略模式"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._instances: Dict[str, BaseCollector] = {}

    # -----------------------------------------------------------
    # 获取单个采集器
    # -----------------------------------------------------------

    def get_collector(self, source_name: str) -> BaseCollector:
        """获取指定数据源的采集器实例（单例）"""
        if source_name not in self._instances:
            collector_cls = _COLLECTOR_REGISTRY.get(source_name)
            if not collector_cls:
                raise ValueError(f"不支持的数据源: {source_name}，可用: {list(_COLLECTOR_REGISTRY.keys())}")
            self._instances[source_name] = collector_cls(self.config)
        return self._instances[source_name]

    # -----------------------------------------------------------
    # 多源数据采集（带故障转移）
    # -----------------------------------------------------------

    def collect_with_fallback(
        self,
        method: str,
        source_order: List[str],
        **kwargs,
    ) -> pd.DataFrame:
        """按优先级顺序采集数据，前一个失败自动切换到下一个
        Args:
            method: 方法名 fetch_realtime_quotes / fetch_history_kline / fetch_stock_basic
            source_order: 数据源优先级列表，如 ["eastmoney", "baostock"]
            **kwargs: 传递给采集器方法的参数
        Returns:
            DataFrame
        """
        errors = []
        for source in source_order:
            try:
                collector = self.get_collector(source)
                func = getattr(collector, method)
                result = func(**kwargs)
                if result is not None and not result.empty:
                    return result
            except Exception as e:
                errors.append(f"[{source}] {e}")
                continue
        # 所有数据源都失败
        raise RuntimeError(f"所有数据源采集失败:\n" + "\n".join(errors))

    # -----------------------------------------------------------
    # 便捷方法
    # -----------------------------------------------------------

    def get_realtime_quotes(self, codes: List[str], prefer: str = "eastmoney") -> pd.DataFrame:
        """获取实时行情（自动故障转移）"""
        source_order = [prefer] + [s for s in ["eastmoney", "baostock", "yahoo"] if s != prefer]
        return self.collect_with_fallback("fetch_realtime_quotes", source_order, codes=codes)

    def get_history_kline(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        freq: str = "daily",
        prefer: str = "baostock",
    ) -> pd.DataFrame:
        """获取历史K线（自动故障转移，优先 baostock 因为数据质量高）"""
        source_order = [prefer] + [s for s in ["baostock", "eastmoney", "yahoo"] if s != prefer]
        return self.collect_with_fallback(
            "fetch_history_kline", source_order,
            code=code, start_date=start_date, end_date=end_date, freq=freq,
        )

    def get_stock_basic(self, codes: List[str] = None, prefer: str = "eastmoney") -> pd.DataFrame:
        """获取股票基本信息"""
        source_order = [prefer] + [s for s in ["eastmoney", "baostock", "yahoo"] if s != prefer]
        return self.collect_with_fallback("fetch_stock_basic", source_order, codes=codes)

    # -----------------------------------------------------------
    # 健康检查
    # -----------------------------------------------------------

    def check_all_sources(self) -> Dict[str, bool]:
        """检查所有注册的数据源是否可达"""
        status = {}
        for name in _COLLECTOR_REGISTRY:
            try:
                collector = self.get_collector(name)
                status[name] = collector.health_check()
            except Exception:
                status[name] = False
        return status

    @staticmethod
    def list_supported_sources() -> List[str]:
        """列出所有可用的数据源"""
        return list(_COLLECTOR_REGISTRY.keys())
