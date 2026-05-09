"""
基金数据采集入口
目前基于东方财富 (akshare) 采集基金净值、持仓等信息

用法:
    # 采集基金净值
    python fund_crawler.py nav 000001 --days 365

    # 列出热门基金
    python fund_crawler.py list
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR


class FundCrawler:
    """基金数据采集器"""

    def __init__(self):
        self.factory = DataSourceFactory()

    def fetch_nav(self, code: str, days: int = 365, save: bool = True):
        """采集基金净值"""
        end = datetime.now()
        start = end - timedelta(days=days)

        print(f"📊 采集基金净值: {code}  {start.strftime('%Y%m%d')}~{end.strftime('%Y%m%d')}")

        collector = self.factory.get_collector("eastmoney")
        df = collector.fetch_fund_nav(
            code=code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )

        if df.empty:
            print("⚠️  未获取到基金净值数据")
            return df

        print(f"✅ 获取到 {len(df)} 条净值记录")
        if save:
            filepath = str(DATA_DIR / f"fund_nav_{code}_{end.strftime('%Y%m%d')}.csv")
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {filepath}")
        return df

    def list_funds(self, limit: int = 20):
        """列出热门基金"""
        print(f"📋 获取热门基金列表 (前 {limit} 只)")
        try:
            import akshare as ak
            df = ak.fund_em_open_fund_rank()
            df = df.head(limit)
            print(df[["基金代码", "基金简称", "日增长率", "近1周", "近1月"]].to_string())
            return df
        except Exception as e:
            print(f"❌ 获取基金列表失败: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="📊 基金数据采集器")
    sub = parser.add_subparsers(dest="command")

    p_nav = sub.add_parser("nav", help="采集基金净值")
    p_nav.add_argument("code", help="基金代码, 如 000001")
    p_nav.add_argument("--days", type=int, default=365)
    p_nav.add_argument("--no-save", action="store_true", help="不保存文件")

    p_list = sub.add_parser("list", help="列出热门基金")
    p_list.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    crawler = FundCrawler()

    if args.command == "nav":
        crawler.fetch_nav(args.code, args.days, save=not args.no_save)
    elif args.command == "list":
        crawler.list_funds(args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
