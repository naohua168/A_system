"""
全市场股票代码源

提供统一的 A 股全市场股票代码列表（沪/深/北交所）。
数据来源：腾讯财经全市场扫描（`fetch_all_realtime`），自动过滤无效代码。

所有需要"全市场"迭代采集的模块通过此模块获取股票列表。
"""
import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger("data_collector.stock_list")


class StockListProvider:
    """全市场股票代码提供者

    从腾讯财经 HTTP 接口扫描所有可能代码（sh6/sz0/sz3/sh9/bj4/bj8 前缀）
    过滤出实际存在的股票，缓存结果避免重复扫描。
    """

    _instance = None
    _cached_codes: Optional[List[str]] = None
    _cached_count: int = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_all_codes(self, force_refresh: bool = False) -> List[str]:
        """获取全市场所有 A 股代码

        Args:
            force_refresh: 是否强制重新扫描（默认使用缓存）
        Returns:
            股票代码列表，如 ["000001", "600519", ...]
        """
        if self._cached_codes is not None and not force_refresh:
            return self._cached_codes

        # 从腾讯财经全市场扫描获取
        from collectors.tencent_collector import TencentCollector
        collector = TencentCollector()
        df = collector.fetch_all_realtime()
        if df.empty:
            logger.warning("全市场扫描失败，返回空列表")
            return []

        codes = sorted(df["code"].unique().tolist())
        self._cached_codes = codes
        self._cached_count = len(codes)
        logger.info("全市场扫描完成：%d 只股票", len(codes))
        return codes

    def get_cached_count(self) -> int:
        """获取缓存中的股票数量"""
        return self._cached_count

    def clear_cache(self):
        """清除缓存（用于强制刷新）"""
        self._cached_codes = None
        self._cached_count = 0


def get_all_stock_codes(force_refresh: bool = False) -> List[str]:
    """便捷函数 — 获取全市场股票代码"""
    return StockListProvider().get_all_codes(force_refresh)
