"""
股票数据采集入口
支持多数据源（东方财富、Baostock、Yahoo Finance）采集 A 股/港股/美股
支持命令行调用和 API 调用两种模式

用法:
    # 采集单只股票历史K线
    python stock_crawler.py kline 000001 --freq daily --days 365

    # 采集多只股票实时行情
    python stock_crawler.py realtime 000001,600519,300750

    # 采集全量股票基本信息
    python stock_crawler.py basic --all

    # 指定数据源
    python stock_crawler.py kline 000001 --source eastmoney --days 90
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR, LOG


class StockCrawler:
    """股票数据采集器入口类"""

    def __init__(self):
        self.factory = DataSourceFactory()

    # -----------------------------------------------------------
    # 实时行情
    # -----------------------------------------------------------

    def fetch_realtime(
        self,
        codes: List[str],
        source: str = "auto",
        save: bool = True,
    ) -> pd.DataFrame:
        """采集实时行情"""
        print(f"📡 采集实时行情: {codes}")
        if source == "auto":
            df = self.factory.get_realtime_quotes(codes)
        else:
            collector = self.factory.get_collector(source)
            df = collector.fetch_realtime_quotes(codes)

        if df.empty:
            print("⚠️  未获取到数据")
            return df

        print(f"✅ 获取到 {len(df)} 条记录")
        if save:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(DATA_DIR / f"realtime_{date_str}.csv")
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {filepath}")
        return df

    # -----------------------------------------------------------
    # 历史K线
    # -----------------------------------------------------------

    def fetch_kline(
        self,
        code: str,
        days: int = 365,
        freq: str = "daily",
        source: str = "auto",
        save: bool = True,
    ) -> pd.DataFrame:
        """采集历史K线"""
        end = datetime.now()
        start = end - timedelta(days=days)
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        print(f"📈 采集历史K线: {code}  {start_str}~{end_str}  freq={freq}")

        if source == "auto":
            df = self.factory.get_history_kline(code, start_str, end_str, freq)
        else:
            collector = self.factory.get_collector(source)
            df = collector.fetch_history_kline(code, start_str, end_str, freq)

        if df.empty:
            print("⚠️  未获取到数据")
            return df

        print(f"✅ 获取到 {len(df)} 条K线数据")
        if save:
            filepath = str(DATA_DIR / f"kline_{code}_{freq}_{end_str}.csv")
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {filepath}")
        return df

    # -----------------------------------------------------------
    # 股票基本信息
    # -----------------------------------------------------------

    def fetch_basic(
        self,
        codes: Optional[List[str]] = None,
        all_stocks: bool = False,
        source: str = "auto",
        save: bool = True,
    ) -> pd.DataFrame:
        """采集股票基本信息"""
        if all_stocks:
            codes = ["*"]
        print(f"📋 采集股票基本信息: 共 {len(codes) if codes else '全部'} 只")

        if source == "auto":
            df = self.factory.get_stock_basic(codes)
        else:
            collector = self.factory.get_collector(source)
            df = collector.fetch_stock_basic(codes)

        if df.empty:
            print("⚠️  未获取到数据")
            return df

        print(f"✅ 获取到 {len(df)} 只股票信息")
        if save:
            date_str = datetime.now().strftime("%Y%m%d")
            filepath = str(DATA_DIR / f"stock_basic_{date_str}.csv")
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {filepath}")
        return df

    # -----------------------------------------------------------
    # 多数据源对比
    # -----------------------------------------------------------

    def compare_sources(self, code: str, days: int = 30) -> dict:
        """对比多个数据源同一只股票的数据"""
        results = {}
        for source in ["eastmoney", "baostock"]:
            try:
                collector = self.factory.get_collector(source)
                df = collector.fetch_history_kline(code, freq="daily")
                results[source] = {
                    "rows": len(df),
                    "date_range": f"{df['date'].min()} ~ {df['date'].max()}" if not df.empty else "N/A",
                }
            except Exception as e:
                results[source] = {"error": str(e)}
        print(f"📊 数据源对比 [{code}]:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return results


def main():
    parser = argparse.ArgumentParser(
        description="📊 多源股票数据采集器 (东方财富 + Baostock + Yahoo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="采集模式")

    # --- realtime 子命令 ---
    p_realtime = sub.add_parser("realtime", help="采集实时行情")
    p_realtime.add_argument("codes", help="股票代码，逗号分隔，如 000001,600519")
    p_realtime.add_argument("--source", default="auto", choices=["auto", "eastmoney", "baostock", "yahoo"])
    p_realtime.add_argument("--no-save", action="store_true", help="不保存到文件")

    # --- kline 子命令 ---
    p_kline = sub.add_parser("kline", help="采集历史K线")
    p_kline.add_argument("code", help="股票代码，如 000001")
    p_kline.add_argument("--freq", default="daily", choices=["daily", "weekly", "monthly"])
    p_kline.add_argument("--days", type=int, default=365, help="拉取天数")
    p_kline.add_argument("--source", default="auto", choices=["auto", "eastmoney", "baostock", "yahoo"])
    p_kline.add_argument("--no-save", action="store_true", help="不保存到文件")

    # --- basic 子命令 ---
    p_basic = sub.add_parser("basic", help="采集股票基本信息")
    p_basic.add_argument("codes", nargs="?", default=None, help="股票代码，逗号分隔")
    p_basic.add_argument("--all", action="store_true", help="采集全部股票")
    p_basic.add_argument("--source", default="auto", choices=["auto", "eastmoney", "baostock", "yahoo"])
    p_basic.add_argument("--no-save", action="store_true", help="不保存到文件")

    # --- compare 子命令 ---
    p_compare = sub.add_parser("compare", help="多数据源对比")
    p_compare.add_argument("code", help="股票代码")
    p_compare.add_argument("--days", type=int, default=30)

    # --- sources 子命令 ---
    sub.add_parser("sources", help="列出所有可用数据源")

    args = parser.parse_args()
    crawler = StockCrawler()

    if args.command == "realtime":
        codes = [c.strip() for c in args.codes.split(",")]
        crawler.fetch_realtime(codes, source=args.source, save=not args.no_save)

    elif args.command == "kline":
        crawler.fetch_kline(
            code=args.code.strip(),
            days=args.days,
            freq=args.freq,
            source=args.source,
            save=not args.no_save,
        )

    elif args.command == "basic":
        codes = [c.strip() for c in args.codes.split(",")] if args.codes else None
        crawler.fetch_basic(codes, all_stocks=args.all, source=args.source, save=not args.no_save)

    elif args.command == "compare":
        crawler.compare_sources(args.code.strip(), args.days)

    elif args.command == "sources":
        sources = DataSourceFactory.list_supported_sources()
        print(f"📦 可用数据源: {', '.join(sources)}")
        for src in sources:
            collector = crawler.factory.get_collector(src)
            print(f"   ├─ {src}: {type(collector).__name__}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
