"""
DataSourceFactory — 数据源工厂（增强版）
根据配置自动选择/组合数据源，支持故障转移 + 指数退避重试 + 熔断 + 限流 + 数据校验
"""

import logging
import time
from typing import Dict, List, Optional

import pandas as pd

from .base_collector import BaseCollector, CircuitBreakerOpenError, DataQualityError
from .mootdx_collector import MootdxCollector
from .tencent_collector import TencentCollector
from .ths_hot_collector import ThsHotCollector, ThsNorthboundCollector
from .baidu_collector import BaiduCollector
from .akshare_extended_collector import AkshareExtendedCollector
from .information_collector import InformationCollector
from config import (
    ENABLED_SOURCES, MAX_RETRIES, RETRY_BACKOFF_BASE,
    VALIDATION, QUALITY_CHECK, RATE_LIMIT, CIRCUIT_BREAKER,
)

logger = logging.getLogger("data_collector.factory")


# 采集器注册表 — 新增数据源只需在这里注册
_COLLECTOR_REGISTRY: Dict[str, type] = {
    "mootdx": MootdxCollector,
    "tencent": TencentCollector,
    "ths_hot": ThsHotCollector,
    "ths_northbound": ThsNorthboundCollector,
    "baidu": BaiduCollector,
    "akshare_ext": AkshareExtendedCollector,
    "information": InformationCollector,       # 资讯层: 研报+新闻+公告
}


class DataSourceFactory:
    """数据源工厂 — 工厂模式 + 策略模式 + 熔断器 + 限流"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._instances: Dict[str, BaseCollector] = {}
        # 限流追踪：记录每个数据源的上次调用时间
        self._last_call_time: Dict[str, float] = {}

    # -----------------------------------------------------------
    # 获取单个采集器
    # -----------------------------------------------------------

    def get_collector(self, source_name: str) -> BaseCollector:
        """获取指定数据源的采集器实例（单例）"""
        if source_name not in self._instances:
            collector_cls = _COLLECTOR_REGISTRY.get(source_name)
            if not collector_cls:
                raise ValueError(
                    f"不支持的数据源: {source_name}，可用: {list(_COLLECTOR_REGISTRY.keys())}"
                )
            if not ENABLED_SOURCES.get(source_name, True):
                raise RuntimeError(f"数据源 {source_name} 已被禁用")
            self._instances[source_name] = collector_cls(self.config)
        return self._instances[source_name]

    # -----------------------------------------------------------
    # 限流 — 避免短时间密集请求触发反爬
    # -----------------------------------------------------------

    def _throttle(self, source_name: str):
        """根据指定数据源的限流间隔等待"""
        if not RATE_LIMIT.get("enabled", False):
            return
        now = time.time()
        interval = RATE_LIMIT.get("min_interval_between_sources", 0.5)
        last = self._last_call_time.get(source_name, 0)
        elapsed = now - last
        if elapsed < interval:
            sleep_time = interval - elapsed
            time.sleep(sleep_time)
        self._last_call_time[source_name] = time.time()

    # -----------------------------------------------------------
    # 数据质量检查
    # -----------------------------------------------------------

    @staticmethod
    def _check_data_quality(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
        """对采集结果进行数据质量检查，返回清洗后的数据"""
        if df.empty:
            return df

        before = len(df)
        max_null_ratio = QUALITY_CHECK.get("max_null_ratio", 0.5)
        max_dup_ratio = QUALITY_CHECK.get("max_duplicate_ratio", 0.3)
        min_rows = QUALITY_CHECK.get("min_rows", 1)

        # 检查空值比例
        # 修复: 先收集所有需要剔除空值的列，再统一删除。避免循环内修改 df 导致后续列计算基准变化
        cols_to_drop = []
        for col in df.columns:
            null_ratio = df[col].isna().sum() / len(df)
            if null_ratio > max_null_ratio and col not in VALIDATION.get("nullable_columns", []):
                logger.warning("[%s] 列 '%s' 空值 %.1f%%，予以剔除", source_name, col, null_ratio * 100)
                cols_to_drop.append(col)
        if cols_to_drop:
            df = df.dropna(subset=cols_to_drop)

        # 检查重复行
        if not df.empty and len(df) > 1:
            dup_ratio = df.duplicated().sum() / len(df)
            if dup_ratio > max_dup_ratio:
                logger.warning("[%s] 重复行 %.1f%%，去重处理", source_name, dup_ratio * 100)
                df = df.drop_duplicates()

        after = len(df)
        if after < min_rows:
            logger.warning("[%s] 有效数据过少: %d 行 (下限 %d)", source_name, after, min_rows)

        if before != after:
            logger.info("[%s] 数据清洗: %d → %d 行", source_name, before, after)
        return df

    # -----------------------------------------------------------
    # 多源数据采集（带故障转移 + 指数退避重试 + 熔断）
    # -----------------------------------------------------------

    def collect_with_fallback(
        self,
        method: str,
        source_order: List[str],
        **kwargs,
    ) -> pd.DataFrame:
        """按优先级顺序采集数据，前一个失败切换到下一个

        增强特性:
        1. 指数退避重试 — 单个数据源内重试 3 次，间隔 1s→2s→4s
        2. 熔断器 — 连续失败 N 次后自动跳过该数据源一段时间
        3. 限流 — 不同数据源间最小调用间隔
        4. 数据质量检查 — 空值/重复行过滤
        """
        errors = []
        for source in source_order:
            if not ENABLED_SOURCES.get(source, True):
                logger.info("[%s] 已被禁用，跳过", source)
                continue

            try:
                collector = self.get_collector(source)
                # 限流
                self._throttle(source)

                func = getattr(collector, method)

                # 使用采集器的重试机制调用
                result = collector._retry_with_backoff(
                    func,
                    max_retries=MAX_RETRIES,
                    backoff_base=RETRY_BACKOFF_BASE,
                    **kwargs,
                )

                if result is None:
                    continue
                if isinstance(result, pd.DataFrame):
                    if result.empty:
                        continue
                    # 数据质量检查
                    result = self._check_data_quality(result, source)
                    if result.empty:
                        continue
                elif isinstance(result, dict):
                    if not result:
                        continue

                logger.info("[%s] 采集成功 (方法=%s)", source, method)
                return result

            except NotImplementedError:
                logger.debug("[%s] 不支持方法 %s，跳过", source, method)
                continue
            except CircuitBreakerOpenError as e:
                logger.warning("[%s] %s", source, e)
                errors.append(f"[{source}] 熔断中")
                continue
            except Exception as e:
                logger.warning("[%s] 采集失败: %s", source, e)
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
        # 修复: 使用 OrderedDict 去重，避免 source_order 中出现重复项或回退链过短
        fallback_chain = ["tencent", "mootdx"]
        source_order = [prefer] + [s for s in fallback_chain if s != prefer]
        return self.collect_with_fallback("fetch_realtime_quotes", source_order, codes=codes)

    def get_history_kline(
        self, code: str,
        start_date: str = None, end_date: str = None,
        freq: str = "daily", prefer: str = "mootdx",
    ) -> pd.DataFrame:
        """获取历史K线（优先 mootdx TCP，速度最快不封IP）"""
        # 修复: 回退到 tencent 而非仅 mootdx
        fallback_chain = ["mootdx", "tencent"]
        source_order = [prefer] + [s for s in fallback_chain if s != prefer]
        return self.collect_with_fallback(
            "fetch_history_kline", source_order,
            code=code, start_date=start_date, end_date=end_date, freq=freq,
        )

    def get_stock_basic(self, codes: List[str] = None,
                        prefer: str = "tencent") -> pd.DataFrame:
        """获取股票基本信息（腾讯财经覆盖全市场）"""
        # 修复: 使用集合去重，避免 prefer=tencent 时 source_order 出现重复
        fallback_chain = ["tencent", "mootdx"]
        source_order = [prefer] + [s for s in fallback_chain if s != prefer]
        return self.collect_with_fallback("fetch_stock_basic", source_order, codes=codes)

    # -----------------------------------------------------------
    # 信号层便捷方法（a-stock-data 新增能力）
    # -----------------------------------------------------------

    def get_hot_reason(self, date_str: str = None) -> pd.DataFrame:
        """当日强势股题材归因（同花顺热点）"""
        collector = self.get_collector("ths_hot")
        self._throttle("ths_hot")
        result = collector._retry_with_backoff(collector.fetch_hot_reason, date_str=date_str)
        if isinstance(result, pd.DataFrame) and not result.empty:
            result = self._check_data_quality(result, "ths_hot")
        return result

    def get_northbound_realtime(self) -> pd.DataFrame:
        """北向资金实时分钟流向"""
        collector = self.get_collector("ths_northbound")
        self._throttle("ths_northbound")
        result = collector._retry_with_backoff(collector.fetch_hsgt_realtime)
        if isinstance(result, pd.DataFrame) and not result.empty:
            result = self._check_data_quality(result, "ths_northbound")
        return result

    def get_northbound_history(self, n: int = 20) -> pd.DataFrame:
        """北向资金历史"""
        collector = self.get_collector("ths_northbound")
        return collector.load_history(n)

    def get_concept_blocks(self, code: str) -> dict:
        """概念板块归属（百度）"""
        collector = self.get_collector("baidu")
        self._throttle("baidu")
        return collector._retry_with_backoff(collector.fetch_concept_blocks, code=code)

    def get_fund_flow(self, code: str, date: str = None) -> list:
        """个股资金流向分钟级（百度）"""
        collector = self.get_collector("baidu")
        self._throttle("baidu")
        return collector._retry_with_backoff(collector.fetch_fund_flow_realtime, code=code, date=date)

    def get_fund_flow_history(self, code: str, days: int = 20) -> list:
        """个股资金流向日级历史（百度）"""
        collector = self.get_collector("baidu")
        return collector.fetch_fund_flow_history(code, days)

    def get_dragon_tiger(self, code: str, trade_date: str) -> dict:
        """龙虎榜席位（akshare）"""
        collector = self.get_collector("akshare_ext")
        self._throttle("akshare_ext")
        return collector._retry_with_backoff(collector.fetch_dragon_tiger_board, code=code, trade_date=trade_date)

    def get_daily_dragon_tiger(self, trade_date: str = None) -> dict:
        """全市场龙虎榜（akshare）"""
        collector = self.get_collector("akshare_ext")
        self._throttle("akshare_ext")
        return collector._retry_with_backoff(collector.fetch_daily_dragon_tiger, trade_date=trade_date)

    def get_lockup_expiry(self, code: str, trade_date: str) -> dict:
        """限售解禁日历（akshare）"""
        collector = self.get_collector("akshare_ext")
        return collector.fetch_lockup_expiry(code, trade_date)

    def get_industry_comparison(self, top_n: int = 20) -> dict:
        """行业横向对比（akshare）"""
        collector = self.get_collector("akshare_ext")
        self._throttle("akshare_ext")
        return collector._retry_with_backoff(collector.fetch_industry_comparison, top_n=top_n)

    # -----------------------------------------------------------
    # 资讯层便捷方法（研报 + 新闻 + 公告 — a-stock-data 合并）
    # 注: get_consensus_eps 从 akshare_ext 迁移到 information 采集器
    # -----------------------------------------------------------

    def get_info_collector(self) -> InformationCollector:
        """获取资讯层采集器实例"""
        return self.get_collector("information")

    def get_research_reports(self, code: str, max_pages: int = 5) -> list:
        """研报列表（东财 reportapi）"""
        collector = self.get_info_collector()
        return collector._retry_with_backoff(
            collector.fetch_research_reports, code=code, max_pages=max_pages
        )

    def download_report_pdf(self, record: dict, target_dir: str = "./reports") -> str:
        """研报PDF下载"""
        collector = self.get_info_collector()
        return collector.download_report_pdf(record, target_dir)

    def get_consensus_eps(self, code: str) -> pd.DataFrame:
        """机构一致预期EPS（同花顺源）"""
        collector = self.get_info_collector()
        self._throttle("information")
        return collector._retry_with_backoff(
            collector.fetch_consensus_eps, code=code
        )

    def get_iwencai_search(self, query: str, api_key: str = None) -> list:
        """iwencai 自然语言研报搜索"""
        collector = self.get_info_collector()
        return collector._retry_with_backoff(
            collector.iwencai_search, query=query, api_key=api_key
        )

    def get_stock_news(self, code: str) -> pd.DataFrame:
        """个股新闻（东财源）"""
        collector = self.get_info_collector()
        self._throttle("information")
        return collector._retry_with_backoff(
            collector.fetch_stock_news, code=code
        )

    def get_cls_news(self) -> pd.DataFrame:
        """财联社快讯"""
        collector = self.get_info_collector()
        self._throttle("information")
        return collector._retry_with_backoff(collector.fetch_cls_news)

    def get_global_news(self) -> pd.DataFrame:
        """全球财经资讯"""
        collector = self.get_info_collector()
        self._throttle("information")
        return collector._retry_with_backoff(collector.fetch_global_news)

    def get_cninfo_filings(self, code: str) -> pd.DataFrame:
        """巨潮公告全文"""
        collector = self.get_info_collector()
        self._throttle("information")
        return collector._retry_with_backoff(
            collector.fetch_cninfo_filings, code=code
        )

    # -----------------------------------------------------------
    # 健康检查
    # -----------------------------------------------------------

    def check_all_sources(self) -> Dict[str, dict]:
        """全面检查各数据源状态（含熔断器状态）"""
        status = {}
        for name in _COLLECTOR_REGISTRY:
            info = {
                "enabled": ENABLED_SOURCES.get(name, True),
                "healthy": False,
                "circuit_breaker": "unknown",
            }
            if not info["enabled"]:
                info["circuit_breaker"] = "disabled"
                status[name] = info
                continue

            try:
                collector = self.get_collector(name)
                info["healthy"] = collector.health_check()
                cb_state = collector._circuit_breaker._s["state"]
                info["circuit_breaker"] = cb_state
            except Exception:
                info["healthy"] = False
            status[name] = info
        return status

    @staticmethod
    def list_supported_sources() -> List[str]:
        return list(_COLLECTOR_REGISTRY.keys())
