"""
DataSourceFactory — 数据源工厂（基于 a-stock-data 重构）
根据配置自动选择/组合数据源，支持故障转移
"""

from typing import Dict, List, Optional

import pandas as pd

from .base_collector import BaseCollector
from .mootdx_collector import MootdxCollector
from .tencent_collector import TencentCollector
from .ths_hot_collector import ThsHotCollector, ThsNorthboundCollector
from .baidu_collector import BaiduCollector
from .akshare_extended_collector import AkshareExtendedCollector


# 采集器注册表 — 新增数据源只需在这里注册
_COLLECTOR_REGISTRY: Dict[str, type] = {
    "mootdx": MootdxCollector,
    "tencent": TencentCollector,
    "ths_hot": ThsHotCollector,
    "ths_northbound": ThsNorthboundCollector,
    "baidu": BaiduCollector,
    "akshare_ext": AkshareExtendedCollector,
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
        """按优先级顺序采集数据，前一个失败切换到下一个"""
        errors = []
        for source in source_order:
            try:
                collector = self.get_collector(source)
                func = getattr(collector, method)
                result = func(**kwargs)
                if result is not None and not result.empty:
                    return result
            except NotImplementedError:
                continue  # 该数据源不支持此方法，跳过
            except Exception as e:
                errors.append(f"[{source}] {e}")
                continue
        raise RuntimeError(f"所有数据源采集失败:\n" + "\n".join(errors))

    # -----------------------------------------------------------
    # 便捷方法（按 a-stock-data 优先级）
    # -----------------------------------------------------------

    def get_realtime_quotes(self, codes: List[str],
                            prefer: str = "tencent") -> pd.DataFrame:
        """获取实时行情（优先腾讯财经，不封IP）
           腾讯财经返回PE/PB/市值等估值数据
           mootdx 返回五档盘口深度行情
        """
        source_order = [prefer] + [s for s in ["tencent", "mootdx"] if s != prefer]
        return self.collect_with_fallback("fetch_realtime_quotes", source_order, codes=codes)

    def get_history_kline(
        self, code: str,
        start_date: str = None, end_date: str = None,
        freq: str = "daily", prefer: str = "mootdx",
    ) -> pd.DataFrame:
        """获取历史K线（优先 mootdx TCP，速度最快不封IP）"""
        source_order = [prefer] + [s for s in ["mootdx"] if s != prefer]
        return self.collect_with_fallback(
            "fetch_history_kline", source_order,
            code=code, start_date=start_date, end_date=end_date, freq=freq,
        )

    def get_stock_basic(self, codes: List[str] = None,
                        prefer: str = "tencent") -> pd.DataFrame:
        """获取股票基本信息（腾讯财经覆盖全市场）"""
        source_order = [prefer] + ["tencent"]
        return self.collect_with_fallback("fetch_stock_basic", source_order, codes=codes)

    # -----------------------------------------------------------
    # 信号层便捷方法（a-stock-data 新增能力）
    # -----------------------------------------------------------

    def get_hot_reason(self, date_str: str = None) -> pd.DataFrame:
        """当日强势股题材归因（同花顺热点）"""
        collector = self.get_collector("ths_hot")
        return collector.fetch_hot_reason(date_str)

    def get_northbound_realtime(self) -> pd.DataFrame:
        """北向资金实时分钟流向"""
        collector = self.get_collector("ths_northbound")
        return collector.fetch_hsgt_realtime()

    def get_northbound_history(self, n: int = 20) -> pd.DataFrame:
        """北向资金历史"""
        collector = self.get_collector("ths_northbound")
        return collector.load_history(n)

    def get_concept_blocks(self, code: str) -> dict:
        """概念板块归属（百度）"""
        collector = self.get_collector("baidu")
        return collector.fetch_concept_blocks(code)

    def get_fund_flow(self, code: str, date: str = None) -> list:
        """个股资金流向分钟级（百度）"""
        collector = self.get_collector("baidu")
        return collector.fetch_fund_flow_realtime(code, date)

    def get_fund_flow_history(self, code: str, days: int = 20) -> list:
        """个股资金流向日级历史（百度）"""
        collector = self.get_collector("baidu")
        return collector.fetch_fund_flow_history(code, days)

    def get_dragon_tiger(self, code: str, trade_date: str) -> dict:
        """龙虎榜席位（akshare）"""
        collector = self.get_collector("akshare_ext")
        return collector.fetch_dragon_tiger_board(code, trade_date)

    def get_daily_dragon_tiger(self, trade_date: str = None) -> dict:
        """全市场龙虎榜（akshare）"""
        collector = self.get_collector("akshare_ext")
        return collector.fetch_daily_dragon_tiger(trade_date)

    def get_lockup_expiry(self, code: str, trade_date: str) -> dict:
        """限售解禁日历（akshare）"""
        collector = self.get_collector("akshare_ext")
        return collector.fetch_lockup_expiry(code, trade_date)

    def get_industry_comparison(self, top_n: int = 20) -> dict:
        """行业横向对比（akshare）"""
        collector = self.get_collector("akshare_ext")
        return collector.fetch_industry_comparison(top_n)

    def get_consensus_eps(self, code: str) -> pd.DataFrame:
        """机构一致预期EPS（akshare）"""
        collector = self.get_collector("akshare_ext")
        return collector.fetch_consensus_eps(code)

    # -----------------------------------------------------------
    # 健康检查
    # -----------------------------------------------------------

    def check_all_sources(self) -> Dict[str, bool]:
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
        return list(_COLLECTOR_REGISTRY.keys())
