"""
并行采集编排器

核心功能：
  1. collect_all() — 并行采集全部 16 种数据类型，按适配器分组避免并发冲突
  2. collect_layers() — 按层（market/signal/information）并行采集
  3. 独立数据类型跨适配器并行执行（ThreadPoolExecutor）
  4. 同适配器类型串行执行（避免过度请求同一端点）
  5. 采集结果分层汇总报告

并行分组规则：
  - 同一数据源（适配器）的类型必须在同一组内串行执行
  - 不同数据源的类型可以跨组并行
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from pipeline.collection_pipeline import CollectionPipeline, CollectReport
from pipeline.data_catalog import get_types_by_layer, get_data_type_def, DataTypeDef

logger = logging.getLogger("data_collector.orchestrator")

# ============================================================
# 并行分组定义
# 每组内串行（同数据源），组间并行（不同数据源）
# ============================================================
PARALLEL_GROUPS: List[List[str]] = [
    # 腾讯财经（同一 HTTP 端点，串行）
    ["realtime_quotes", "stock_basic"],

    # 同花顺热点（独立端点）
    ["hot_reason"],

    # 同花顺北向资金（独立端点）
    ["northbound"],

    # 百度 PAE（同一协议，串行）
    ["concept_blocks", "fund_flow"],

    # akshare 扩展（同一第三方库，串行）
    ["dragon_tiger_daily", "industry_compare", "lockup_expiry"],

    # 资讯层采集器（同一 collector 实例，串行）
    ["research_reports", "consensus_eps", "stock_news",
     "cls_news", "global_news", "filings"],

    # mootdx 通达信 TCP（独立，逐股迭代）
    ["history_kline"],
]

# 构建反向映射：data_type → group_index
_DATA_TYPE_GROUP: Dict[str, int] = {}
for gidx, group in enumerate(PARALLEL_GROUPS):
    for dt in group:
        _DATA_TYPE_GROUP[dt] = gidx


def get_group_index(data_type: str) -> int:
    """获取数据类型所属的并行分组索引"""
    return _DATA_TYPE_GROUP.get(data_type, -1)


def get_all_data_types() -> List[str]:
    """获取所有注册的数据类型"""
    from pipeline.data_catalog import DATA_CATALOG
    types_set: set = set()
    for group in PARALLEL_GROUPS:
        types_set.update(group)
    # 再补充 data_catalog 中但未在分组中注册的类型（兜底）
    for d in DATA_CATALOG:
        types_set.add(d.data_type)
    return list(types_set)


# ============================================================
# 扩展采集报告 — 支持分层汇总
# ============================================================
class LayerReport:
    """分层采集报告 — 按层汇总"""

    def __init__(self):
        self.raw = {}                # data_type → CollectReport item
        self.layers: Dict[str, List[str]] = {
            "market": [],
            "signal": [],
            "information": [],
            "unknown": [],
        }

    def record(self, data_type: str, item: dict):
        """记录单类型采集结果，自动归类到对应层"""
        self.raw[data_type] = item
        try:
            td = get_data_type_def(data_type)
            layer = td.layer
        except KeyError:
            layer = "unknown"
        if data_type not in self.layers[layer]:
            self.layers[layer].append(data_type)

    def summary(self) -> str:
        """生成分层采集报告"""
        lines = []
        lines.append(f"\n{'='*65}")
        lines.append(f"📊 全量并行采集报告  ({datetime.now():%Y-%m-%d %H:%M:%S})")
        lines.append(f"{'='*65}")

        grand_total = 0
        grand_ok = 0
        grand_types = len(self.raw)

        layer_names = {
            "market": "行情层",
            "signal": "信号层",
            "information": "资讯层",
        }

        for layer, type_list in self.layers.items():
            if not type_list:
                continue
            layer_total = 0
            layer_ok = 0
            lines.append(f"\n{'─'*65}")
            lines.append(f"  █ {layer_names.get(layer, layer)} ({len(type_list)} 种)")
            lines.append(f"{'─'*65}")
            for dt in type_list:
                item = self.raw.get(dt)
                if not item:
                    lines.append(f"  ❌ {dt:28s} 未执行")
                    continue
                icon = "✅" if item["success"] else "❌"
                rows = item["rows"]
                elapsed = item["elapsed_s"]
                adapter = f"[{item['adapter_used']}]" if item.get("adapter_used") else ""
                lines.append(f"  {icon} {dt:28s} {adapter} {rows:>8,}行 {elapsed:>8.2f}s")
                if item["success"]:
                    layer_ok += 1
                    layer_total += rows
            grand_ok += layer_ok
            grand_total += layer_total
            lines.append(f"  {'─'*65}")
            lines.append(f"  小计: ✅ {layer_ok}/{len(type_list)}  共 {layer_total:,} 行")

        lines.append(f"\n{'='*65}")
        lines.append(f"  📦 总计: ✅ {grand_ok}/{grand_types}  共 {grand_total:,} 行")
        lines.append(f"{'='*65}")
        return "\n".join(lines)


# ============================================================
# 并行采集编排器
# ============================================================
class ParallelCollector:
    """并行采集编排器

    用法:
        pc = ParallelCollector()
        layer_report = pc.collect_all()               # 采集全部16种
        layer_report = pc.collect_layer("signal")      # 只采信号层
        layer_report = pc.collect_types(["realtime_quotes", "hot_reason"])  # 指定类型
    """

    def __init__(self, max_workers: int = 4, max_stocks: int = 0):
        """
        Args:
            max_workers: 并行线程数（默认4，避免过度请求外部API）
            max_stocks:  全市场迭代时的最大股票数，0=全部
        """
        self.max_workers = max_workers
        self.max_stocks = max_stocks
        self._pipeline_cache: Dict[str, CollectionPipeline] = {}

    def _get_pipeline(self) -> CollectionPipeline:
        """获取或创建 pipeline 实例"""
        if "default" not in self._pipeline_cache:
            self._pipeline_cache["default"] = CollectionPipeline(
                max_stocks=self.max_stocks,
            )
        return self._pipeline_cache["default"]

    # -----------------------------------------------------------
    # 核心：按并行分组执行
    # -----------------------------------------------------------

    def collect_types(self, data_types: List[str],
                      codes: Optional[List[str]] = None) -> LayerReport:
        """并行采集指定数据类型列表

        自动按适配器分组，组内串行、组间并行。
        """
        report = LayerReport()

        if not data_types:
            return report

        # 按分组索引重新组织
        groups: Dict[int, List[str]] = {}
        for dt in data_types:
            gidx = get_group_index(dt)
            if gidx not in groups:
                groups[gidx] = []
            groups[gidx].append(dt)

        # 每个分组提交一个任务，组内串行
        def _run_group(group_types: List[str]) -> Dict[str, dict]:
            """串行执行一个分组内的所有类型"""
            pipeline = self._get_pipeline()
            group_results = {}
            for dt in group_types:
                t0 = time.time()
                try:
                    pipeline.run(dt, codes=codes)
                    item = pipeline.report.items.get(dt, {})
                except Exception as e:
                    item = {
                        "rows": 0, "success": False,
                        "elapsed_s": round(time.time() - t0, 2),
                        "adapter_used": "error",
                        "error": str(e)[:100],
                    }
                group_results[dt] = item
            return group_results

        # 提交到线程池执行
        futures = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for gidx, type_list in groups.items():
                if not type_list:
                    continue
                future = executor.submit(_run_group, type_list)
                futures[future] = type_list

            # 收集结果
            for future in as_completed(futures):
                group_types = futures[future]
                try:
                    group_results = future.result()
                    for dt, item in group_results.items():
                        report.record(dt, item)
                except Exception as e:
                    for dt in group_types:
                        report.record(dt, {
                            "rows": 0, "success": False,
                            "elapsed_s": 0, "adapter_used": "error",
                            "error": str(e)[:100],
                        })

        return report

    # -----------------------------------------------------------
    # 按层采集
    # -----------------------------------------------------------

    def collect_layer(self, layer: str,
                      codes: Optional[List[str]] = None) -> LayerReport:
        """采集指定层的所有数据类型"""
        types = [d.data_type for d in get_types_by_layer(layer)]
        return self.collect_types(types, codes)

    # -----------------------------------------------------------
    # 全量采集
    # -----------------------------------------------------------

    def collect_all(self, codes: Optional[List[str]] = None) -> LayerReport:
        """采集全部 16 种数据类型（所有层）"""
        all_types = get_all_data_types()
        return self.collect_types(all_types, codes)

    # -----------------------------------------------------------
    # 快速采集：只采全局类型（一次性全量，无需逐股迭代）
    # -----------------------------------------------------------

    def collect_global_only(self) -> LayerReport:
        """只采集 is_global=True 的全局类型（最快，无需逐股迭代）"""
        from pipeline.data_catalog import DATA_CATALOG
        global_types = [d.data_type for d in DATA_CATALOG if d.is_global]
        return self.collect_types(global_types)

    def close(self):
        for p in self._pipeline_cache.values():
            p.close()
