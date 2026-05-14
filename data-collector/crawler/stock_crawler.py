"""
股票数据采集入口（基于 a-stock-data 重构）
数据源: mootdx(通达信TCP) / 腾讯财经 / 同花顺热点 / 百度PAE / akshare扩展
支持命令行和 API 两种模式

用法:
    # ===== 基础行情 =====
    python stock_crawler.py kline 688017 --days 365
    python stock_crawler.py realtime 000001,600519,300750
    python stock_crawler.py basic 000001 --all

    # ===== 信号层（a-stock-data 新增）=====
    python stock_crawler.py hot-reason 2026-05-12
    python stock_crawler.py northbound
    python stock_crawler.py concept 688017
    python stock_crawler.py fund-flow 000858 --days 20
    python stock_crawler.py dragon-tiger 002475 2026-05-12
    python stock_crawler.py daily-dragon-tiger 2026-05-12
    python stock_crawler.py lockup 002475 2026-05-12
    python stock_crawler.py industry-compare
    python stock_crawler.py consensus-eps 688017
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR


class StockCrawler:
    """股票数据采集器入口类（基于 a-stock-data）"""

    def __init__(self):
        self.factory = DataSourceFactory()

    # ==========================================================
    # 基础行情
    # ==========================================================

    def fetch_realtime(self, codes: List[str], source: str = "auto",
                       save: bool = True) -> pd.DataFrame:
        """采集实时行情（腾讯财经/mootdx）"""
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
            fp = str(DATA_DIR / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.csv")
            df.to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {fp}")
        return df

    def fetch_kline(self, code: str, days: int = 365, freq: str = "daily",
                    source: str = "auto", save: bool = True) -> pd.DataFrame:
        """采集历史K线（mootdx TCP）"""
        end = datetime.now()
        start = end - timedelta(days=days)
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")
        print(f"📈 采集K线: {code}  {start_str}~{end_str}  freq={freq}")
        if source == "auto":
            df = self.factory.get_history_kline(code, start_str, end_str, freq)
        else:
            collector = self.factory.get_collector(source)
            df = collector.fetch_history_kline(code, start_str, end_str, freq)
        if df.empty:
            print("⚠️  未获取到数据")
            return df
        print(f"✅ 获取到 {len(df)} 条K线")
        if save:
            fp = str(DATA_DIR / f"kline_{code}_{freq}_{end_str}.csv")
            df.to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {fp}")
        return df

    def fetch_basic(self, codes: Optional[List[str]] = None,
                    all_stocks: bool = False, source: str = "auto",
                    save: bool = True) -> pd.DataFrame:
        """采集股票基本信息（腾讯财经）"""
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
            fp = str(DATA_DIR / f"stock_basic_{datetime.now():%Y%m%d}.csv")
            df.to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {fp}")
        return df

    # ==========================================================
    # 信号层（a-stock-data 新增）
    # ==========================================================

    def fetch_hot_reason(self, date_str: str = None):
        """当日强势股题材归因（同花顺热点）"""
        print(f"🔥 采集当日强势股题材归因")
        df = self.factory.get_hot_reason(date_str)
        if df.empty:
            print("⚠️  未获取到数据（盘后15:30后更新）")
            return df
        print(f"✅ 当日强势股 {len(df)} 只")
        print(df[["代码", "名称", "涨幅%", "题材归因"]].head(20).to_string())
        return df

    def fetch_northbound(self):
        """北向资金实时流向"""
        print("🌐 北向资金实时分钟流向")
        df = self.factory.get_northbound_realtime()
        if df.empty:
            print("⚠️  未获取到数据")
            return df
        print(f"✅ 分钟点数: {len(df)}")
        print(df.tail(5).to_string())
        return df

    def fetch_concept(self, code: str):
        """概念板块归属"""
        print(f"🏷️  概念板块归属: {code}")
        result = self.factory.get_concept_blocks(code)
        print(f"行业: {[b['name'] for b in result['industry']]}")
        print(f"概念: {result['concept_tags']}")
        print(f"地域: {[b['name'] for b in result['region']]}")
        return result

    def fetch_fund_flow(self, code: str, days: int = 20):
        """个股资金流向"""
        print(f"💧 个股资金流向: {code}")
        history = self.factory.get_fund_flow_history(code, days)
        if not history:
            print("⚠️  未获取到数据")
            return history
        print(f"最近 {len(history)} 日:")
        for h in history[:10]:
            print(f"  {h['date']}: 主力={h['mainIn']}万 超大单={h['superNetIn']}万")
        return history

    def fetch_dragon_tiger(self, code: str, trade_date: str):
        """龙虎榜席位"""
        print(f"🐯 龙虎榜席位: {code} (截至{trade_date})")
        data = self.factory.get_dragon_tiger(code, trade_date)
        print(f"近30日上榜 {len(data['records'])} 次")
        for r in data["records"]:
            print(f"  {r['date']}: {r['reason']}")
        if data["seats"]["buy"]:
            print("买入席位TOP5:")
            for s in data["seats"]["buy"]:
                print(f"  {s['name']}: 买{s['buy_amt']}万 卖{s['sell_amt']}万 净{s['net']}万")
        return data

    def fetch_daily_dragon_tiger(self, trade_date: str = None):
        """全市场龙虎榜"""
        print("📊 全市场龙虎榜")
        data = self.factory.get_daily_dragon_tiger(trade_date)
        print(f"{data['date']} 共 {data['total_records']} 条")
        for s in data["stocks"][:10]:
            print(f"  {s['code']} {s['name']}: {s['reason']} | 净买{s['net_buy_wan']}万 涨跌{s['change_pct']}%")
        return data

    def fetch_lockup(self, code: str, trade_date: str):
        """限售解禁日历"""
        print(f"🔒 限售解禁: {code}")
        data = self.factory.get_lockup_expiry(code, trade_date)
        print(f"历史解禁 {len(data['history'])} 批")
        for h in data["history"][:5]:
            print(f"  {h['date']}: {h['type']} 数量={h['shares']}")
        if data["upcoming"]:
            print(f"未来90天待解禁 {len(data['upcoming'])} 批:")
            for u in data["upcoming"]:
                print(f"  {u['date']}: {u['type']} 占流通{u['float_ratio']}%")
        return data

    def fetch_industry_compare(self, top_n: int = 20):
        """行业横向对比"""
        print("📊 行业横向对比")
        data = self.factory.get_industry_comparison(top_n)
        print(f"共 {data['total']} 个行业")
        print("TOP 10 涨幅:")
        for r in data["top"][:10]:
            print(f"  {r['rank']}. {r['name']}: {r['change_pct']}% 成交{r['turnover_yi']}亿 领涨{r['leader']}")
        print("BOTTOM 3 跌幅:")
        for r in data["bottom"][-3:]:
            print(f"  {r['rank']}. {r['name']}: {r['change_pct']}%")
        return data

    def fetch_consensus_eps(self, code: str):
        """机构一致预期EPS"""
        print(f"📈 机构一致预期EPS: {code}")
        df = self.factory.get_consensus_eps(code)
        if df.empty:
            print("⚠️  无机构覆盖")
            return df
        print(df.to_string())
        return df


def main():
    parser = argparse.ArgumentParser(
        description="📊 股票数据采集器 (a-stock-data: mootdx+腾讯+同花顺+百度+龙虎榜+解禁+行业)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="采集模式")

    # --- 基础行情 ---
    p_realtime = sub.add_parser("realtime", help="实时行情(腾讯/mootdx)")
    p_realtime.add_argument("codes", help="股票代码逗号分隔")
    p_realtime.add_argument("--source", default="auto", choices=["auto", "tencent", "mootdx"])
    p_realtime.add_argument("--no-save", action="store_true")

    p_kline = sub.add_parser("kline", help="历史K线(mootdx)")
    p_kline.add_argument("code", help="股票代码")
    p_kline.add_argument("--freq", default="daily", choices=["daily","weekly","monthly","5min","15min","30min","60min"])
    p_kline.add_argument("--days", type=int, default=365)
    p_kline.add_argument("--source", default="auto", choices=["auto", "mootdx"])
    p_kline.add_argument("--no-save", action="store_true")

    p_basic = sub.add_parser("basic", help="股票基本信息(腾讯)")
    p_basic.add_argument("codes", nargs="?", default=None)
    p_basic.add_argument("--all", action="store_true")
    p_basic.add_argument("--source", default="auto", choices=["auto", "tencent"])
    p_basic.add_argument("--no-save", action="store_true")

    # --- 信号层 ---
    sub.add_parser("hot-reason", help="当日强势股题材归因")
    sub.add_parser("northbound", help="北向资金实时流向")

    p_concept = sub.add_parser("concept", help="概念板块归属")
    p_concept.add_argument("code", help="股票代码")

    p_flow = sub.add_parser("fund-flow", help="个股资金流向")
    p_flow.add_argument("code", help="股票代码")
    p_flow.add_argument("--days", type=int, default=20)

    p_dt = sub.add_parser("dragon-tiger", help="龙虎榜席位")
    p_dt.add_argument("code", help="股票代码")
    p_dt.add_argument("trade_date", help="YYYY-MM-DD")

    sub.add_parser("daily-dragon-tiger", help="全市场龙虎榜")

    p_lockup = sub.add_parser("lockup", help="限售解禁日历")
    p_lockup.add_argument("code", help="股票代码")
    p_lockup.add_argument("trade_date", help="YYYY-MM-DD")

    p_ind = sub.add_parser("industry-compare", help="行业横向对比")
    p_ind.add_argument("--top", type=int, default=20)

    p_eps = sub.add_parser("consensus-eps", help="机构一致预期EPS")
    p_eps.add_argument("code", help="股票代码")

    sub.add_parser("sources", help="列出可用数据源")

    args = parser.parse_args()
    crawler = StockCrawler()

    # 基础行情
    if args.command == "realtime":
        crawler.fetch_realtime([c.strip() for c in args.codes.split(",")], args.source, not args.no_save)
    elif args.command == "kline":
        crawler.fetch_kline(args.code.strip(), args.days, args.freq, args.source, not args.no_save)
    elif args.command == "basic":
        codes = [c.strip() for c in args.codes.split(",")] if args.codes else None
        crawler.fetch_basic(codes, args.all, args.source, not args.no_save)
    # 信号层
    elif args.command == "hot-reason":
        crawler.fetch_hot_reason()
    elif args.command == "northbound":
        crawler.fetch_northbound()
    elif args.command == "concept":
        crawler.fetch_concept(args.code)
    elif args.command == "fund-flow":
        crawler.fetch_fund_flow(args.code, args.days)
    elif args.command == "dragon-tiger":
        crawler.fetch_dragon_tiger(args.code, args.trade_date)
    elif args.command == "daily-dragon-tiger":
        crawler.fetch_daily_dragon_tiger()
    elif args.command == "lockup":
        crawler.fetch_lockup(args.code, args.trade_date)
    elif args.command == "industry-compare":
        crawler.fetch_industry_compare(args.top)
    elif args.command == "consensus-eps":
        crawler.fetch_consensus_eps(args.code)
    elif args.command == "sources":
        sources = DataSourceFactory.list_supported_sources()
        print(f"📦 可用数据源 ({len(sources)}):")
        for src in sources:
            c = crawler.factory.get_collector(src)
            print(f"  ├─ {src}: {type(c).__name__}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
