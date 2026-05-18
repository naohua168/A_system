"""
采集管道 — 编排 适配器.fetch() → 校验 → 存储 的端到端流程

核心流程:
  1. 根据 data_type 查找 DataCatalog 定义
  2. 按优先级遍历适配器列表（故障转移）
  3. 适配器.fetch(request) → pd.DataFrame
  4. 数据质量检查
  5. StorageManager.write(table, df)
  6. 返回采集报告

设计目标:
  - 所有数据采集走此管道，不再直接调适配器
  - 前端永不直接调适配器，只读 StorageManager
  - 单数据源失败不阻塞全流程
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from adapters.base_adapter import AdapterRegistry, AdapterRequest
from pipeline.data_catalog import DataTypeDef, StorageTarget, get_data_type_def
from storage.storage_manager import StorageManager

logger = logging.getLogger("data_collector.pipeline")


class CollectReport:
    """采集报告 — 记录每次管道执行的结果"""

    def __init__(self):
        self.items: Dict[str, dict] = {}

    def record(self, data_type: str, rows: int, success: bool,
               elapsed: float, adapter_used: str = "",
               storage_results: Optional[Dict] = None):
        self.items[data_type] = {
            "rows": rows,
            "success": success,
            "elapsed_s": round(elapsed, 2),
            "adapter_used": adapter_used,
            "storage": storage_results or {},
        }

    def summary(self) -> str:
        lines = [f"\n{'='*55}", "📊 采集管道报告", f"{'='*55}"]
        total_ok = sum(1 for v in self.items.values() if v["success"])
        total_rows = sum(v["rows"] for v in self.items.values())
        lines.append(f"  成功: {total_ok}/{len(self.items)}  总行数: {total_rows}")
        lines.append(f"{'-'*55}")
        for dt, info in self.items.items():
            icon = "✅" if info["success"] else "❌"
            adapter = f"[{info['adapter_used']}]" if info["adapter_used"] else ""
            lines.append(f"  {icon} {dt:25s} {adapter} {info['rows']:>6}行 {info['elapsed_s']:>6.2f}s")
        lines.append(f"{'='*55}")
        return "\n".join(lines)


class CollectionPipeline:
    """数据采集管道

    用法:
        pipeline = CollectionPipeline()
        report = pipeline.run("realtime_quotes")            # 全市场实时行情
        report = pipeline.run("history_kline")               # 迭代全市场K线
        report = pipeline.run("research_reports")            # 迭代全市场研报
    """

    def __init__(self, storage: Optional[StorageManager] = None,
                 max_stocks: int = 0):
        """
        Args:
            storage: 存储管理器实例
            max_stocks: 全市场迭代时的最大股票数，0=不限制（全量采集）
        """
        self.storage = storage or StorageManager()
        self.report = CollectReport()
        self.max_stocks = max_stocks

    def run(self, data_type: str, codes: Optional[List[str]] = None,
            params: Optional[Dict] = None) -> CollectReport:
        """执行单类型采集

        Args:
            data_type: 数据类型标识
            codes: 指定股票列表；None 表示全市场
            params: 扩展参数
        Returns:
            CollectReport 实例
        """
        type_def = get_data_type_def(data_type)
        t0 = time.time()

        # 构建请求，注入 data_type 供适配器分发使用
        sys_extra = {"data_type": data_type, "focus": data_type}
        user_extra = (params or {}).pop("extra", {}) if params else {}
        merged_extra = {**sys_extra, **user_extra}
        merged_params = {**(params or {}), "extra": merged_extra}

        # 判断是否为全市场采集模式
        is_full_market = codes is None
        if is_full_market:
            if type_def.is_global:
                # 全局类型 — 不传 codes，适配器一次性拉取全部
                request = AdapterRequest(**merged_params)
                df, adapter_used = self._collect_with_fallback(type_def, request)
            else:
                # 逐只股票迭代模式 — 遍历全市场股票
                df, adapter_used = self._collect_all_stocks(type_def, merged_params)
        else:
            # 指定部分股票
            request = AdapterRequest(
                codes=codes,
                **merged_params,
            )
            df, adapter_used = self._collect_with_fallback(type_def, request)

        success = not df.empty

        # 存储
        storage_results = {}
        if success and type_def.storage.mysql_table:
            storage_results = self.storage.write(
                type_def.storage.mysql_table, df,
                backends=["csv", "mysql"],
            )

        # 记录报告
        elapsed = time.time() - t0
        self.report.record(
            data_type=data_type,
            rows=len(df),
            success=success,
            elapsed=elapsed,
            adapter_used=adapter_used,
            storage_results=storage_results,
        )
        return self.report

    def _collect_all_stocks(self, type_def: DataTypeDef,
                             params: Optional[Dict] = None) -> tuple:
        """遍历全市场所有股票，逐只采集

        用于 K线、研报、新闻、公告、资金流向 等需要逐只股票调用的数据类型。
        """
        from collectors.stock_list import get_all_stock_codes
        all_codes = get_all_stock_codes()
        if self.max_stocks > 0:
            all_codes = all_codes[:self.max_stocks]

        adapters = AdapterRegistry.get_adapters(type_def.data_type)
        if not adapters:
            return pd.DataFrame(), ""

        all_dfs = []
        total = len(all_codes)
        success_count = 0
        params = params or {}

        for idx, code in enumerate(all_codes):
            request = AdapterRequest(
                code=code,
                codes=[code],
                **(params),
            )
            for adapter in adapters:
                try:
                    df = adapter.fetch(request)
                    if df is not None and not df.empty:
                        all_dfs.append(df)
                        success_count += 1
                        break
                except NotImplementedError:
                    continue
                except Exception as e:
                    logger.debug("[%s] %s 采集失败: %s",
                                 type_def.data_type, code, e)
                    continue

            if (idx + 1) % 500 == 0:
                logger.info("[%s] 进度 %d/%d (%.1f%%)，成功 %d 只",
                            type_def.data_type, idx + 1, total,
                            (idx + 1) / total * 100, success_count)

        result = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
        logger.info("[%s] 全市场采集完成: %d/%d 成功, 共 %d 行",
                    type_def.data_type, success_count, total, len(result))
        return result, adapters[0].metadata.source_name if adapters else ""

    def run_many(self, data_types: List[str],
                 codes: Optional[List[str]] = None) -> CollectReport:
        """批量采集多种数据类型"""
        for dt in data_types:
            print(f"\n[{datetime.now():%H:%M:%S}] 📦 采集 {dt}")
            try:
                self.run(dt, codes=codes)
            except Exception as e:
                logger.error("批量采集 [%s] 失败: %s", dt, e)
                self.report.record(dt, 0, False, 0.0, adapter_used="error")
        return self.report

    def run_layer(self, layer: str,
                  codes: Optional[List[str]] = None) -> CollectReport:
        """采集某层所有数据类型"""
        from pipeline.data_catalog import get_types_by_layer
        types = [d.data_type for d in get_types_by_layer(layer)]
        return self.run_many(types, codes)

    def _collect_with_fallback(self, type_def: DataTypeDef,
                                request: AdapterRequest) -> tuple:
        """按优先级遍历适配器，实现故障转移"""
        adapters = AdapterRegistry.get_adapters(type_def.data_type)
        if not adapters:
            logger.warning("[%s] 无注册适配器", type_def.data_type)
            return pd.DataFrame(), ""

        last_error = None
        for adapter in adapters:
            try:
                df = adapter.fetch(request)
                if df is not None and not df.empty:
                    logger.info("[%s] 采集成功 via %s (pri=%d)",
                                type_def.data_type,
                                adapter.metadata.source_name,
                                adapter.metadata.priority)
                    return df, adapter.metadata.source_name
                logger.debug("[%s] via %s 返回空数据",
                             type_def.data_type, adapter.metadata.source_name)
            except NotImplementedError:
                continue
            except Exception as e:
                last_error = e
                logger.warning("[%s] via %s 失败: %s",
                               type_def.data_type,
                               adapter.metadata.source_name, e)
                continue

        error_msg = f"所有适配器失败: {last_error}" if last_error else "无可用适配器"
        logger.error("[%s] %s", type_def.data_type, error_msg)
        return pd.DataFrame(), ""

    def close(self):
        self.storage.close()
