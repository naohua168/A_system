"""
K线数据主控脚本 — 一站式采集 → 同步MySQL → 多周期聚合

功能:
  1. 全市场日K线采集（mootdx TCP 优先 → 新浪HTTP回退）
  2. 实时同步到MySQL stock_daily 表
  3. 日K→周K/月K聚合
  4. 断线重连 + 指数退避 + 增量恢复
  5. 数据覆盖报告

用法:
    python kline_master.py                              # 全量K线采集+同步+聚合
    python kline_master.py --stocks 100                 # 仅前100只（测试用）
    python kline_master.py --years 3                    # 回溯3年
    python kline_master.py --sync-only                  # 仅同步已有CSV到MySQL
    python kline_master.py --aggregate-only             # 仅聚合日K→周K/月K
    python kline_master.py --incremental                # 增量模式（补最近数据）
"""
import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import DATA_DIR, DEFAULT_KLINE_YEARS, KLINE_COLLECT_INTERVAL
from collectors.stock_list import get_all_stock_codes

logger = logging.getLogger("data_collector.kline_master")

# 报告计数器
_total_collected = 0
_total_synced = 0
_total_aggregated = 0
_start_time = None


def print_banner(msg: str):
    print(f"\n{'=' * 55}")
    print(f"  {msg}")
    print(f"{'=' * 55}")


# ============================================================
# 阶段1: K线采集
# ============================================================
def collect_all_kline(stock_codes: List[str], years: int,
                      max_stocks: int = 0) -> int:
    """全市场K线采集（带断线重连 + 指数退避）"""
    from market_collect import HttpOnlyCollector

    if max_stocks > 0:
        stock_codes = stock_codes[:max_stocks]

    total = len(stock_codes)
    print_banner(f"📈 K线采集 [{datetime.now():%H:%M:%S}] codes={total}")

    collector = HttpOnlyCollector()
    results = collector.collect_kline(
        codes=stock_codes,
        years=years,
        freq="daily",
        sync_mysql=False,       # 阶段2单独处理
        aggregate_weekly=False,
        aggregate_monthly=False,
    )
    global _total_collected
    _total_collected = sum(results.values())
    return _total_collected


# ============================================================
# 阶段2: 同步到MySQL
# ============================================================
def sync_kline_to_mysql(incremental: bool = False) -> int:
    """将K线CSV同步到MySQL stock_daily表"""
    print_banner(f"📤 同步K线到MySQL [{datetime.now():%H:%M:%S}]")

    try:
        from scheduler.sync_to_mysql import DataSync
        syncer = DataSync(verbose=True)
        count = syncer.sync_all()
        syncer.close()
        global _total_synced
        _total_synced = count
        return count
    except Exception as e:
        print(f"  ❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


# ============================================================
# 阶段3: 多周期聚合
# ============================================================
def aggregate_kline(stock_codes: List[str], max_stocks: int = 0,
                    incremental: bool = False) -> int:
    """日K→周K/月K聚合"""
    print_banner(f"🔄 多周期聚合 [{datetime.now():%H:%M:%S}]")

    from scheduler.aggregate_kline import KlineAggregator
    aggr = KlineAggregator()
    try:
        if max_stocks > 0:
            stock_codes = stock_codes[:max_stocks]
        results = aggr.aggregate_all(stock_codes, max_stocks=0, incremental=incremental)
        total_w = sum(v[0] for v in results.values())
        total_m = sum(v[1] for v in results.values())
        global _total_aggregated
        _total_aggregated = total_w + total_m
        return _total_aggregated
    finally:
        aggr.close()


# ============================================================
# 阶段4: 数据覆盖报告
# ============================================================
def print_coverage_report():
    """输出stock_daily表数据覆盖报告"""
    print_banner("📊 K线数据覆盖报告")
    total_stocks = len(get_all_stock_codes())

    try:
        import pymysql
        from config import MYSQL_CONFIG
        conn = pymysql.connect(
            host=MYSQL_CONFIG["host"], port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"], password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"], charset="utf8mb4",
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_daily")
            row = cur.fetchone()
            covered = row[0] if row else 0

            cur.execute("SELECT COUNT(*) FROM stock_daily")
            total_rows = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT stock_code, COUNT(*) as cnt,
                       MIN(trade_date) as first_date,
                       MAX(trade_date) as last_date
                FROM stock_daily
                GROUP BY stock_code
                ORDER BY cnt DESC LIMIT 5
            """)
            top5 = cur.fetchall()

            cur.execute("""
                SELECT stock_code, COUNT(*) as cnt
                FROM stock_daily
                GROUP BY stock_code
                ORDER BY cnt ASC LIMIT 5
            """)
            bottom5 = cur.fetchall()
        conn.close()

        print(f"  全市场股票: {total_stocks}")
        print(f"  有日K数据:  {covered} / {total_stocks} ({covered/total_stocks*100:.1f}%)" if covered > 0 else "  有日K数据:  0")
        print(f"  日K总行数:  {total_rows:,}")
        print()
        print("  📈 数据最多的TOP5只:")
        for row in top5:
            print(f"    {row[0]}: {row[1]:>4}条 ({row[2]}~{row[3]})")
        print()
        if bottom5:
            print("  📉 数据最少TOP5只:")
            for row in bottom5:
                print(f"    {row[0]}: {row[1]:>4}条")

        # 周K/月K覆盖
        with conn.cursor() as cur:
            for tbl, label in [("stock_kline_weekly", "周K"), ("stock_kline_monthly", "月K")]:
                cur.execute(f"SELECT COUNT(DISTINCT stock_code) FROM {tbl}")
                c = cur.fetchone()[0] or 0
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                r = cur.fetchone()[0] or 0
                print(f"  {label}: {c} 只股票, {r} 条")

    except Exception as e:
        print(f"  ⚠️  无法读取MySQL: {e}")

    print(f"\n  ⏱  总耗时: {time.time() - _start_time:.0f}s" if _start_time else "")
    print(f"  📥 采集: {_total_collected:,} 条")
    print(f"  📤 同步: {_total_synced} 文件")
    print(f"  🔄 聚合: {_total_aggregated:,} 条")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="K线数据主控 — 采集→同步→聚合")
    parser.add_argument("--stocks", type=int, default=0,
                        help="采集股票数（0=全市场）")
    parser.add_argument("--years", type=int, default=DEFAULT_KLINE_YEARS,
                        help="回溯年数")
    parser.add_argument("--sync-only", action="store_true",
                        help="仅同步已有CSV到MySQL")
    parser.add_argument("--aggregate-only", action="store_true",
                        help="仅聚合日K→周K/月K")
    parser.add_argument("--incremental", action="store_true",
                        help="增量模式")
    parser.add_argument("--report-only", action="store_true",
                        help="仅输出覆盖报告")
    args = parser.parse_args()

    global _start_time
    _start_time = time.time()

    stock_codes = get_all_stock_codes()
    logging.basicConfig(level=logging.INFO)

    try:
        if args.report_only:
            print_coverage_report()
            return

        if args.sync_only:
            sync_kline_to_mysql(incremental=args.incremental)
            print_coverage_report()
            return

        if args.aggregate_only:
            aggregate_kline(stock_codes, max_stocks=args.stocks,
                            incremental=args.incremental)
            print_coverage_report()
            return

        # 全流程: 采集 → 同步 → 聚合
        collect_all_kline(stock_codes, args.years, max_stocks=args.stocks)
        sync_kline_to_mysql(incremental=args.incremental)
        aggregate_kline(stock_codes, max_stocks=args.stocks,
                        incremental=args.incremental)
        print_coverage_report()

        print(f"\n{'=' * 55}")
        print(f"  🏁 K线全流程完成 [{datetime.now():%H:%M:%S}]")
        print(f"{'=' * 55}")

    except KeyboardInterrupt:
        print("\n\n  ⛔ 用户中断")
        print_coverage_report()
    except Exception as e:
        print(f"\n  ❌ 流程异常: {e}")
        import traceback
        traceback.print_exc()
        print_coverage_report()


if __name__ == "__main__":
    main()
