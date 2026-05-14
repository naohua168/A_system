"""
统一数据采集调度脚本
支持一次性全量/增量采集，以及定时调度

用法:
    # 全量采集（所有数据源）
    python run_collector.py --all

    # 仅采集实时行情
    python run_collector.py --realtime

    # 采集信号层数据（热点/北向/行业对比）
    python run_collector.py --signals

    # 采集指定股票的全量数据
    python run_collector.py --stock 688017

    # 采集后同步到数据库
    python run_collector.py --all --sync

    # 定时循环采集（每30分钟）
    python run_collector.py --loop 30
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR


class DataCollectorRunner:
    """统一数据采集调度器"""

    def __init__(self):
        self.factory = DataSourceFactory()
        self.results = {}

    # ==========================================================
    # 行情层
    # ==========================================================

    def collect_realtime(self, codes: list = None) -> pd.DataFrame:
        """采集实时行情（腾讯财经，含PE/PB/市值）"""
        if codes is None:
            codes = ["000001", "600519", "300750", "688017", "002463"]
        print(f"[{datetime.now():%H:%M:%S}] 📡 实时行情: {codes}")
        try:
            df = self.factory.get_realtime_quotes(codes)
            self._save("realtime", df)
            return df
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            return pd.DataFrame()

    def collect_kline(self, codes: list = None, days: int = 365) -> dict:
        """采集历史K线（mootdx）"""
        if codes is None:
            codes = ["000001", "600519", "300750", "688017", "002463"]
        results = {}
        for code in codes:
            print(f"[{datetime.now():%H:%M:%S}] 📈 K线: {code}")
            try:
                df = self.factory.get_history_kline(code, freq="daily")
                if not df.empty:
                    self._save(f"kline_{code}", df)
                    results[code] = len(df)
                    print(f"   ✅ {len(df)} 条")
                else:
                    print("   ⚠️  无数据")
            except Exception as e:
                print(f"   ❌ {e}")
            time.sleep(0.5)
        return results

    # ==========================================================
    # 信号层
    # ==========================================================

    def collect_hot_reason(self) -> pd.DataFrame:
        """当日强势股题材归因"""
        print(f"[{datetime.now():%H:%M:%S}] 🔥 题材归因")
        try:
            df = self.factory.get_hot_reason()
            if not df.empty:
                self._save("hot_reason", df)
                print(f"   ✅ 强势股 {len(df)} 只")
            return df
        except Exception as e:
            print(f"   ❌ {e}")
            return pd.DataFrame()

    def collect_northbound(self) -> pd.DataFrame:
        """北向资金"""
        print(f"[{datetime.now():%H:%M:%S}] 🌐 北向资金")
        try:
            df = self.factory.get_northbound_realtime()
            if not df.empty:
                self._save("northbound", df)
                # 自动缓存收盘数据
                last = df.dropna().iloc[-1]
                nbc = self.factory.get_collector("ths_northbound")
                nbc.save_daily_snapshot(datetime.now().strftime("%Y-%m-%d"),
                                         last["hgt_yi"], last["sgt_yi"])
                print(f"   ✅ 分钟点数 {len(df)}")
            return df
        except Exception as e:
            print(f"   ❌ {e}")
            return pd.DataFrame()

    def collect_industry_compare(self) -> dict:
        """行业横向对比"""
        print(f"[{datetime.now():%H:%M:%S}] 📊 行业对比")
        try:
            data = self.factory.get_industry_comparison(20)
            if data["total"] > 0:
                self._save_json("industry_compare", data)
                print(f"   ✅ {data['total']} 个行业")
            return data
        except Exception as e:
            print(f"   ❌ {e}")
            return {}

    def collect_stock_signals(self, codes: list = None) -> dict:
        """采集个股信号层数据（概念板块+资金流向）"""
        if codes is None:
            codes = ["000001", "600519", "300750"]
        results = {}
        today = datetime.now().strftime("%Y-%m-%d")
        for code in codes:
            signals = {}
            print(f"[{datetime.now():%H:%M:%S}] 📶 信号: {code}")
            try:
                signals["concept"] = self.factory.get_concept_blocks(code)
            except Exception as e:
                signals["concept_error"] = str(e)
            try:
                signals["fund_flow"] = self.factory.get_fund_flow_history(code, 5)
            except Exception as e:
                signals["fund_flow_error"] = str(e)
            try:
                signals["dragon_tiger"] = self.factory.get_dragon_tiger(code, today)
            except Exception as e:
                signals["dragon_tiger_error"] = str(e)
            try:
                signals["lockup"] = self.factory.get_lockup_expiry(code, today)
            except Exception as e:
                signals["lockup_error"] = str(e)
            self._save_json(f"signals_{code}", signals)
            results[code] = {k: v for k, v in signals.items() if not k.endswith("_error")}
            time.sleep(1)
        return results

    # ==========================================================
    # 全量采集
    # ==========================================================

    def collect_all(self):
        """全量采集"""
        print(f"\n{'='*50}")
        print(f"📦 全量数据采集启动 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}\n")

        self.collect_hot_reason()
        self.collect_northbound()
        self.collect_industry_compare()
        self.collect_realtime()
        self.collect_kline()

        print(f"\n{'='*50}")
        print(f"🏁 全量采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}")

    # ==========================================================
    # 工具方法
    # ==========================================================

    def _save(self, prefix: str, df: pd.DataFrame):
        """保存DataFrame到CSV"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = DATA_DIR / f"{prefix}_{ts}.csv"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(fp, index=False, encoding="utf-8-sig")

    def _save_json(self, prefix: str, data: dict):
        """保存字典到JSON"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = DATA_DIR / f"{prefix}_{ts}.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="统一数据采集调度脚本 (a-stock-data)")
    parser.add_argument("--all", action="store_true", help="全量采集")
    parser.add_argument("--realtime", action="store_true", help="仅采集实时行情")
    parser.add_argument("--kline", action="store_true", help="仅采集K线")
    parser.add_argument("--signals", action="store_true", help="仅采集信号层数据")
    parser.add_argument("--stock", type=str, help="指定股票代码采集")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔（分钟），0=不循环")

    args = parser.parse_args()
    runner = DataCollectorRunner()

    def run_once():
        if args.all:
            runner.collect_all()
        elif args.realtime:
            runner.collect_realtime()
        elif args.kline:
            runner.collect_kline()
        elif args.signals:
            runner.collect_hot_reason()
            runner.collect_northbound()
            runner.collect_industry_compare()
        elif args.stock:
            runner.collect_stock_signals([args.stock])
        else:
            parser.print_help()
            return

    if args.loop > 0:
        print(f"🔄 定时采集启动，间隔 {args.loop} 分钟")
        while True:
            run_once()
            print(f"\n⏳ 等待 {args.loop} 分钟后下次采集...\n")
            time.sleep(args.loop * 60)
    else:
        run_once()


if __name__ == "__main__":
    main()
