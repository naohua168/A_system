"""
具体适配器实现 — 包装现有的 BaseCollector 子类，使其符合 DataSourceAdapter 协议

每个适配器通过 AdapterRegistry 注册到对应 data_type。
适配器内部持有 Collector 实例，调用原始方法并归一化返回值为 pd.DataFrame。

设计重点:
  1. 将现有的 .fetch_xxx() 方法封装为统一 .fetch(request)
  2. 不管原始返回 dict/list/DataFrame，适配器层统一输出 DataFrame
  3. 列名固定为 snake_case，前端不依赖原始数据源字段名
  4. 所有适配器在模块加载时自动注册到 AdapterRegistry
"""

import logging
from typing import List, Optional

import pandas as pd

from adapters.base_adapter import (
    AdapterMetadata, AdapterRegistry, AdapterRequest, DataSourceAdapter,
)
from collectors.data_source_factory import DataSourceFactory

logger = logging.getLogger("adapters.collector_wrapper")


# ============================================================
# 适配器基类 — 包装采集器
# ============================================================
class CollectorAdapter(DataSourceAdapter):
    """适配器基类 — 包装 BaseCollector 实例"""

    def __init__(self, source_name: str, priority: int,
                 supported_types: List[str], description: str = ""):
        self._metadata = AdapterMetadata(
            source_name=source_name,
            priority=priority,
            supported_data_types=supported_types,
            description=description,
        )
        self._factory = DataSourceFactory()
        self._collector = None

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    @property
    def collector(self):
        if self._collector is None:
            self._collector = self._factory.get_collector(self.metadata.source_name)
        return self._collector

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        raise NotImplementedError

    def check_health(self) -> bool:
        return self.collector.health_check()

    @staticmethod
    def _resolve_code(request: AdapterRequest) -> Optional[str]:
        """从请求中提取股票代码，无代码时返回 None 而非硬编码默认值"""
        return request.code or (request.codes[0] if request.codes else None)


# ============================================================
# 腾讯财经适配器
# ============================================================
class TencentAdapter(CollectorAdapter):
    """腾讯财经 — 实时行情+估值数据"""

    def __init__(self):
        super().__init__(
            source_name="tencent", priority=9,
            supported_types=["realtime_quotes", "stock_basic"],
            description="HTTP直连实时行情+PE/PB/市值/换手率",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        if request.codes:
            return self.collector.fetch_realtime_quotes(request.codes)
        return self.collector.fetch_all_realtime()


# ============================================================
# Mootdx（通达信TCP）适配器
# ============================================================
class MootdxAdapter(CollectorAdapter):
    """mootdx — K线+盘口+逐笔"""

    def __init__(self):
        super().__init__(
            source_name="mootdx", priority=10,
            supported_types=["history_kline", "realtime_quotes"],
            description="TCP直连通达信，最稳定不封IP",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        if request.extra.get("method") == "kline" or request.code:
            return self.collector.fetch_history_kline(
                code=request.code or (request.codes[0] if request.codes else ""),
                start_date=request.start_date,
                end_date=request.end_date,
                freq=request.freq,
            )
        if request.codes:
            return self.collector.fetch_realtime_quotes(request.codes)
        return pd.DataFrame()


# ============================================================
# 同花顺热点适配器
# ============================================================
class ThsHotAdapter(CollectorAdapter):
    """同花顺 — 强势股题材归因"""

    def __init__(self):
        super().__init__(
            source_name="ths_hot", priority=8,
            supported_types=["hot_reason"],
            description="零鉴权73ms当日强势股+题材归因",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        return self.collector.fetch_hot_reason(date_str=request.date_str)


class ThsNorthboundAdapter(CollectorAdapter):
    """同花顺 — 北向资金"""

    def __init__(self):
        super().__init__(
            source_name="ths_northbound", priority=8,
            supported_types=["northbound"],
            description="北向资金实时分钟流向",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        return self.collector.fetch_hsgt_realtime()


# ============================================================
# 百度PAE适配器
# ============================================================
class BaiduAdapter(CollectorAdapter):
    """百度股市通 — 概念板块+资金流向"""

    def __init__(self):
        super().__init__(
            source_name="baidu", priority=7,
            supported_types=["concept_blocks", "fund_flow"],
            description="PAE协议概念板块+资金流向",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        raw_focus = request.extra.get("focus", "")
        focus_map = {"concept_blocks": "concept", "fund_flow": "fund"}
        focus = focus_map.get(raw_focus, raw_focus)
        code = request.code or (request.codes[0] if request.codes else None)
        if code is None:
            return pd.DataFrame()
        if "concept" in focus:
            # 概念板块: 归一化为 DataFrame
            try:
                result = self.collector.fetch_concept_blocks(code)
            except Exception as e:
                logger.warning("概念板块采集失败 [%s]: %s", code, e)
                return pd.DataFrame()
            records = []
            for block_type in ["industry", "concept", "region"]:
                for item in result.get(block_type, []):
                    records.append({
                        "stock_code": code,
                        "block_type": block_type,
                        "block_name": item.get("name", ""),
                        "change_pct": item.get("change_pct", ""),
                        "description": item.get("desc", ""),
                        "source": self.metadata.source_name,
                    })
            # 标签扁平化
            for tag in result.get("concept_tags", []):
                records.append({
                    "stock_code": code,
                    "block_type": "concept_tag",
                    "block_name": tag,
                    "change_pct": "",
                    "description": "",
                    "source": self.metadata.source_name,
                })
            return pd.DataFrame(records) if records else pd.DataFrame()

        # 资金流向
        try:
            history = self.collector.fetch_fund_flow_history(code, request.days or 20)
        except Exception as e:
            logger.warning("资金流向采集失败 [%s]: %s", code, e)
            return pd.DataFrame()
        if not history:
            return pd.DataFrame()
        df = pd.DataFrame(history)
        df["stock_code"] = code
        df["source"] = self.metadata.source_name
        return df


# ============================================================
# akshare 扩展适配器
# ============================================================
class AkshareAdapter(CollectorAdapter):
    """akshare扩展 — 龙虎榜/解禁/行业对比"""

    def __init__(self):
        super().__init__(
            source_name="akshare_ext", priority=6,
            supported_types=["dragon_tiger_daily", "industry_compare", "lockup_expiry"],
            description="akshare扩展龙虎榜/解禁/行业",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        # 兼容旧 focus 短名 和 新 data_type 全名
        focus_map = {
            "dragon_tiger_daily": "dragon_tiger",
            "industry_compare": "industry",
            "lockup_expiry": "lockup",
        }
        raw_focus = request.extra.get("focus", request.extra.get("data_type", ""))
        focus = focus_map.get(raw_focus, raw_focus)

        if focus == "dragon_tiger":
            result = self.collector.fetch_daily_dragon_tiger(
                trade_date=request.date_str,
                min_net_buy=request.extra.get("min_net_buy"),
            )
            df = pd.DataFrame(result.get("stocks", []))
            if not df.empty:
                df["trade_date"] = result.get("date", request.date_str)
            return df

        if focus == "industry":
            result = self.collector.fetch_industry_comparison(top_n=request.top_n)
            records = result.get("top", [])
            # flatten: top + bottom 合并
            bottom = result.get("bottom", [])
            for b in bottom:
                b["rank"] = b.get("rank", 0) + len(records)
            records.extend(bottom)
            df = pd.DataFrame(records)
            if not df.empty:
                df["fetch_date"] = request.date_str or ""
            return df

        if focus == "lockup":
            code = self._resolve_code(request)
            if code is None:
                return pd.DataFrame()
            result = self.collector.fetch_lockup_expiry(
                code=code,
                trade_date=request.date_str or "",
            )
            records = []
            for h in result.get("history", []):
                h["type_tag"] = "history"
                records.append(h)
            for u in result.get("upcoming", []):
                u["type_tag"] = "upcoming"
                records.append(u)
            df = pd.DataFrame(records)
            if not df.empty:
                df["stock_code"] = code
            return df

        return pd.DataFrame()


# ============================================================
# 资讯层适配器
# ============================================================
class InformationAdapter(CollectorAdapter):
    """资讯层 — 研报+新闻+公告"""

    def __init__(self):
        super().__init__(
            source_name="information", priority=5,
            supported_types=[
                "research_reports", "consensus_eps",
                "stock_news", "cls_news", "global_news", "filings",
            ],
            description="研报/新闻/公告统一入口",
        )

    def fetch(self, request: AdapterRequest) -> pd.DataFrame:
        # 优先使用外部传入的 focus，否则从 data_type 自动派生
        focus = request.extra.get("focus", request.extra.get("data_type", ""))
        # 兼容旧调用方：research_reports → research
        if focus == "research_reports":
            focus = "research"

        code = self._resolve_code(request)
        if code is None and focus in ("research", "consensus_eps", "stock_news", "filings"):
            return pd.DataFrame()

        ACTION_MAP = {
            "research": lambda: pd.DataFrame(
                self.collector.fetch_research_reports(
                    code=code,
                    max_pages=request.max_pages,
                ) or []
            ),
            "consensus_eps": lambda: (
                lambda df: df.assign(stock_code=code) if not df.empty else df
            )(self.collector.fetch_consensus_eps(code=code)),
            "stock_news": lambda: self.collector.fetch_stock_news(code=code),
            "cls_news": lambda: self.collector.fetch_cls_news(),
            "global_news": lambda: self.collector.fetch_global_news(),
            "filings": lambda: self.collector.fetch_cninfo_filings(code=code),
        }

        action = ACTION_MAP.get(focus)
        if action:
            return action()
        return pd.DataFrame()


# ============================================================
# 模块加载时自动注册到 AdapterRegistry
# ============================================================
def register_all_adapters():
    """注册所有适配器到全局注册表"""
    adapters = [
        TencentAdapter(),
        MootdxAdapter(),
        ThsHotAdapter(),
        ThsNorthboundAdapter(),
        BaiduAdapter(),
        AkshareAdapter(),
        InformationAdapter(),
    ]

    for adapter in adapters:
        for data_type in adapter.get_supported_types():
            AdapterRegistry.register(data_type, adapter)

    logger.info("适配器注册完成: %d types, %d adapters",
                len(AdapterRegistry.get_all_types()), len(adapters))
