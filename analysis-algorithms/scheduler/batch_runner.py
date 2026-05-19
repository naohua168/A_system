"""
批量分析调度器 — 全市场/增量/单股三种运行模式

与 L2 run_batch_pipeline.py 对应，延续统一接口规范:

  模式         触发条件        范围
  ─────────    ────────────   ─────────────────
  daily        每日收盘后     全市场所有活跃股票 × 全量分析
  incremental  滚动增量       最近交易日热门/涨幅前 100 只
  single       按需调用       指定单只股票

用法:
  # 全量跑批
  python -m scheduler.batch_runner --mode daily

  # 增量（仅扫描涨幅前 100）
  python -m scheduler.batch_runner --mode incremental --top 100

  # 单股
  python -m scheduler.batch_runner --mode single --code 000001
"""

import argparse
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from engine.orchestrator import AnalysisEngine

logger = logging.getLogger("analysis.scheduler")

# 默认配置
DEFAULT_DAYS = 365
DEFAULT_TOP_N = 100
DEFAULT_MAX_WORKERS = 4


class BatchRunner:
    """批量分析调度器"""

    def __init__(self, mysql_config: Optional[Dict] = None,
                 redis_host: str = "localhost"):
        self.engine = AnalysisEngine(mysql_config, redis_host)

    # ============================================================
    # daily: 全市场全量分析
    # ============================================================

    def run_daily(self, max_stocks: int = 0) -> Dict[str, Dict]:
        """每日全量跑批：全市场股票全量分析

        Args:
            max_stocks: 限制分析股票数（0=全部），调试用
        Returns:
            分析结果 {stock_code: result}
        """
        logger.info("=" * 50)
        logger.info("  L3 全量跑批启动 (%s)", datetime.now().isoformat())
        logger.info("=" * 50)

        t_start = time.time()
        all_stocks = self.engine.loader.read_all_stocks()

        if all_stocks.empty:
            logger.warning("无股票数据，请确认 MySQL 是否已采集")
            return {}

        codes = all_stocks["stock_code"].tolist()
        if max_stocks > 0:
            codes = codes[:max_stocks]

        logger.info("待分析股票: %d 只", len(codes))

        results = self.engine.analyze_batch(
            codes, days=DEFAULT_DAYS,
            parallel=True, max_workers=DEFAULT_MAX_WORKERS,
        )

        elapsed = time.time() - t_start
        ok_count = sum(
            1 for r in results.values() if "error" not in r
        )
        fail_count = len(results) - ok_count

        logger.info("=" * 50)
        logger.info("  全量跑批完成: 成功 %d / 失败 %d / 耗时 %.1fs",
                     ok_count, fail_count, elapsed)
        logger.info("=" * 50)

        return results

    # ============================================================
    # incremental: 增量分析（热门/涨幅居前）
    # ============================================================

    def run_incremental(self, top_n: int = DEFAULT_TOP_N) -> Dict[str, Dict]:
        """增量分析：只分析涨幅/热度最高的股票

        Args:
            top_n: 分析前 N 只热门股
        Returns:
            分析结果
        """
        logger.info("L3 增量跑批 (%s): TOP %d", datetime.now().isoformat(), top_n)

        all_stocks = self.engine.loader.read_all_stocks()
        if all_stocks.empty:
            return {}

        # 按涨跌幅倒排取前 N
        if "change_percent" in all_stocks.columns:
            hot = all_stocks.sort_values("change_percent", ascending=False)
        else:
            # 按总市值排序兜底
            hot = all_stocks.sort_values("total_market_cap", ascending=False)
        codes = hot["stock_code"].head(top_n).tolist()

        logger.info("增量分析股票: %d 只", len(codes))
        return self.engine.analyze_batch(
            codes, days=DEFAULT_DAYS,
            parallel=True, max_workers=DEFAULT_MAX_WORKERS,
        )

    # ============================================================
    # single: 单只股票分析
    # ============================================================

    def run_single(self, code: str, persist: bool = True) -> Dict:
        """单只股票全量分析

        Args:
            code: 股票代码
            persist: 是否持久化结果
        Returns:
            分析结果
        """
        logger.info("L3 单股分析: %s", code)
        return self.engine.analyze_stock(code, days=DEFAULT_DAYS,
                                          with_chanlun=True,
                                          with_quantitative=True,
                                          persist=persist)

    # ============================================================
    # 清理过期结果
    # ============================================================

    def cleanup(self, keep_days: int = 30) -> int:
        """清理过期分析结果

        Args:
            keep_days: 保留最近 N 天
        Returns:
            清理记录数
        """
        logger.info("L3 清理过期结果 (保留 %d 天)", keep_days)
        total = 0
        from datetime import timedelta, date as dt_date
        from data.loader import DataLoader
        loader = DataLoader()
        conn = loader._get_mysql()
        cursor = conn.cursor()
        cutoff = (dt_date.today() - timedelta(days=keep_days)).isoformat()
        try:
            for atype in ("full", "technical", "chanlun", "quantitative"):
                cursor.execute(
                    "DELETE FROM analysis_result "
                    "WHERE analysis_type=%s AND analysis_date < %s",
                    (atype, cutoff),
                )
                conn.commit()
                deleted = cursor.rowcount
                if deleted:
                    logger.info("清理 %s: %d 条", atype, deleted)
                    total += deleted
        except Exception as e:
            logger.warning("清理失败: %s", e)
        finally:
            cursor.close()
            loader.close()
        return total

    def close(self):
        self.engine.close()


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="L3 算法分析层调度器")
    parser.add_argument(
        "--mode", choices=["daily", "incremental", "single", "cleanup"],
        default="single",
        help="运行模式: daily(全量) / incremental(增量) / single(单股) / cleanup(清理)",
    )
    parser.add_argument("--code", default="000001", help="股票代码 (single 模式)")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N,
                        help="增量分析 TOP N (incremental 模式)")
    parser.add_argument("--max", type=int, default=0,
                        help="全量分析最大股票数 (daily 模式, 0=全部)")
    parser.add_argument("--keep-days", type=int, default=30,
                        help="清理保留天数 (cleanup 模式)")
    parser.add_argument("--no-persist", action="store_true",
                        help="不持久化结果到 MySQL")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    runner = BatchRunner()
    try:
        if args.mode == "daily":
            runner.run_daily(max_stocks=args.max)
        elif args.mode == "incremental":
            runner.run_incremental(top_n=args.top)
        elif args.mode == "single":
            result = runner.run_single(args.code, persist=not args.no_persist)
            print(f"\n分析完成: {args.code}")
            print(f"  技术指标: {len(result.get('technical', {}))}项")
            print(f"  缠论: {'✅' if result.get('chanlun') else '❌'}")
            print(f"  量化: {'✅' if result.get('quantitative') else '❌'}")
            print(f"  耗时: {result.get('elapsed_ms', 0)}ms")
        elif args.mode == "cleanup":
            deleted = runner.cleanup(keep_days=args.keep_days)
            print(f"清理完毕: {deleted} 条")
    finally:
        runner.close()


if __name__ == "__main__":
    main()
