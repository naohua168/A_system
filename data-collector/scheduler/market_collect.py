"""
HTTP + TCP 全协议数据采集脚本
支持6个数据源（5个HTTP直连 + 1个TCP通达信）：

  采集器          | 协议  | 数据类型
  ─────────────────┼───────┼──────────────────────────────
  tencent         | HTTP  | 实时行情+PE/PB/市值/换手率
  ths_hot         | HTTP  | 强势股题材归因+热点
  ths_northbound  | HTTP  | 北向资金实时分钟流向
  baidu           | HTTP  | 概念板块+个股资金流向
  akshare_ext     | HTTP  | 龙虎榜/解禁/行业对比/研报/公告
  mootdx          | TCP   | K线(多周期)/五档盘口/逐笔成交/财务快照/F10

用法:
    python market_collect.py                    # HTTP全量采集(默认)
    python market_collect.py --tcp              # HTTP + TCP K线采集
    python market_collect.py --standalone       # 独立模式(零工厂依赖)
    python market_collect.py --sync             # HTTP采集+同步MySQL

Tips:
  - Windows PowerShell 可直接运行
  - TCP模式需要: pip install mootdx
  - 首次运行前: pip install pandas requests akshare
  - data/ 目录自动创建，采集结果随时可删
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR


# ============================================================
# 采集测试股票（覆盖沪深创业板）
# ============================================================
TEST_CODES = ["000001", "600519", "300750", "002463", "688017",
              "000858", "600036", "601318", "002415", "300059"]


class HttpOnlyCollector:
    """HTTP专属采集器 — 仅使用HTTP直连数据源"""

    def __init__(self):
        self.factory = DataSourceFactory()
        self.results = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    # 1. 实时行情（腾讯财经 HTTP）
    # ----------------------------------------------------------
    def collect_realtime(self, codes: list = None) -> pd.DataFrame:
        """采集实时行情 + PE/PB/市值"""
        if codes is None:
            codes = TEST_CODES
        print(f"[{datetime.now():%H:%M:%S}] 📡 实时行情 (腾讯) codes={len(codes)}")
        try:
            df = self.factory.get_realtime_quotes(codes)
            if not df.empty:
                fp = DATA_DIR / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 条 -> {fp.name}")
            else:
                print("  ⚠️  空数据")
            return df
        except Exception as e:
            print(f"  ❌ {e}")
            return pd.DataFrame()

    # ----------------------------------------------------------
    # 2. 股票基本信息（腾讯财经 HTTP）
    # ----------------------------------------------------------
    def collect_basic(self, codes: list = None) -> pd.DataFrame:
        """采集股票基本信息"""
        if codes is None:
            codes = TEST_CODES
        print(f"[{datetime.now():%H:%M:%S}] 📋 股票基本信息 (腾讯)")
        try:
            df = self.factory.get_stock_basic(codes)
            if not df.empty:
                fp = DATA_DIR / f"stock_basic_{datetime.now():%Y%m%d}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 只 -> {fp.name}")
            else:
                print("  ⚠️  空数据")
            return df
        except Exception as e:
            print(f"  ❌ {e}")
            return pd.DataFrame()

    # ----------------------------------------------------------
    # 3. 题材热点（同花顺 HTTP）
    # ----------------------------------------------------------
    def collect_hot_reason(self) -> pd.DataFrame:
        """当日强势股题材归因"""
        print(f"[{datetime.now():%H:%M:%S}] 🔥 题材归因 (同花顺)")
        try:
            df = self.factory.get_hot_reason()
            if not df.empty:
                fp = DATA_DIR / f"hot_reason_{datetime.now():%Y%m%d}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 只强势股 -> {fp.name}")
                return df
        except Exception as e:
            print(f"  ❌ {e}")
        return pd.DataFrame()

    # ----------------------------------------------------------
    # 4. 北向资金（同花顺 HTTP）
    # ----------------------------------------------------------
    def collect_northbound(self) -> pd.DataFrame:
        """北向资金实时分钟流向"""
        print(f"[{datetime.now():%H:%M:%S}] 🌐 北向资金 (同花顺)")
        try:
            df = self.factory.get_northbound_realtime()
            if not df.empty:
                fp = DATA_DIR / f"northbound_{datetime.now():%Y%m%d}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 分钟数据 -> {fp.name}")
                return df
        except Exception as e:
            print(f"  ❌ {e}")
        return pd.DataFrame()

    # ----------------------------------------------------------
    # 5. 行业对比（akshare HTTP）
    # ----------------------------------------------------------
    def collect_industry_compare(self) -> dict:
        print(f"[{datetime.now():%H:%M:%S}] 📊 行业对比 (akshare)")
        try:
            data = self.factory.get_industry_comparison(20)
            if data.get("total", 0) > 0:
                fp = DATA_DIR / f"industry_compare_{datetime.now():%Y%m%d}.json"
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  ✅ {data['total']} 个行业 -> {fp.name}")
                return data
        except Exception as e:
            print(f"  ❌ {e}")
        return {}

    # ----------------------------------------------------------
    # 6. 概念板块（百度 HTTP）
    # ----------------------------------------------------------
    def collect_concept_blocks(self, codes: list = None) -> dict:
        if codes is None:
            codes = TEST_CODES[:3]
        print(f"[{datetime.now():%H:%M:%S}] 🏷️  概念板块 (百度)")
        results = {}
        for code in codes:
            try:
                data = self.factory.get_concept_blocks(code)
                results[code] = data
                print(f"  {code}: 行业{len(data.get('industry',[]))} 概念{len(data.get('concept_tags',[]))}个")
            except Exception as e:
                print(f"  {code}: ❌ {e}")
            time.sleep(0.3)
        fp = DATA_DIR / f"concept_blocks_{datetime.now():%Y%m%d}.json"
        fp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return results

    # ----------------------------------------------------------
    # 7. 个股资金流向（百度 HTTP）
    # ----------------------------------------------------------
    def collect_fund_flow(self, codes: list = None, days: int = 10) -> dict:
        if codes is None:
            codes = TEST_CODES[:3]
        print(f"[{datetime.now():%H:%M:%S}] 💧 资金流向 (百度)")
        results = {}
        for code in codes:
            try:
                history = self.factory.get_fund_flow_history(code, days)
                results[code] = {"days": len(history), "data": history[:3]}
                print(f"  {code}: {len(history)} 日")
            except Exception as e:
                print(f"  {code}: ❌ {e}")
            time.sleep(0.3)
        fp = DATA_DIR / f"fund_flow_{datetime.now():%Y%m%d}.json"
        fp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return results

    # ----------------------------------------------------------
    # 8. 龙虎榜（akshare HTTP）
    # ----------------------------------------------------------
    def collect_dragon_tiger(self, trade_date: str = None) -> dict:
        print(f"[{datetime.now():%H:%M:%S}] 🐯 龙虎榜 (akshare)")
        if trade_date is None:
            from datetime import date as _date
            trade_date = _date.today().strftime("%Y-%m-%d")
        try:
            data = self.factory.get_daily_dragon_tiger(trade_date)
            if data.get("total_records", 0) > 0:
                fp = DATA_DIR / f"dragon_tiger_{trade_date}.json"
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  ✅ {data['total_records']} 条记录 -> {fp.name}")
                return data
        except Exception as e:
            print(f"  ❌ {e}")
        return {}

    # ----------------------------------------------------------
    # 9. TCP K线（mootdx — 通达信 TCP 7709端口）
    # ----------------------------------------------------------
    def collect_kline(self, codes: list = None, years: int = 2) -> dict:
        """通过 mootdx TCP 采集历史K线数据"""
        if codes is None:
            codes = TEST_CODES
        print(f"[{datetime.now():%H:%M:%S}] 📈 TCP K线 (mootdx) codes={len(codes)}")
        results = {}
        try:
            collector = self.factory.get_collector("mootdx")
        except Exception as e:
            print(f"  ❌ mootdx 不可用: {e}（pip install mootdx 或检查国内IP）")
            return results

        from datetime import timedelta
        end = datetime.now()
        start = (end - timedelta(days=years * 365)).strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        for code in codes:
            try:
                df = collector.fetch_history_kline(code, start, end_str, freq="daily")
                if not df.empty:
                    fp = DATA_DIR / f"kline_{code}_daily_{end:%Y%m%d}.csv"
                    df.to_csv(fp, index=False, encoding="utf-8-sig")
                    print(f"  ✅ {code}: {len(df)} 根K线 -> {fp.name}")
                    results[code] = len(df)
                else:
                    print(f"  ⚠️  {code}: 无数据")
            except Exception as e:
                print(f"  ❌ {code}: {e}")
            time.sleep(0.5)
        return results

    # ----------------------------------------------------------
    # TCP全量采集（K线 + 实时行情）
    # ----------------------------------------------------------
    def collect_tcp_all(self):
        print(f"\n{'='*55}")
        print(f"📡 HTTP + TCP 全量采集 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}\n")

        # HTTP 层
        self.collect_basic()
        self.collect_realtime()
        self.collect_hot_reason()
        self.collect_northbound()
        self.collect_industry_compare()

        # TCP 层（mootdx K线）
        self.collect_kline()

        print(f"\n{'='*55}")
        print(f"🏁 全量采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}")

    # ----------------------------------------------------------
    # 全量HTTP采集
    # ----------------------------------------------------------
    def collect_all(self):
        print(f"\n{'='*55}")
        print(f"📦 HTTP全量采集 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}\n")

        # 1. 基本行情
        self.collect_basic()
        self.collect_realtime()

        # 2. 信号层
        self.collect_hot_reason()
        self.collect_northbound()
        self.collect_industry_compare()
        self.collect_concept_blocks()
        self.collect_fund_flow()

        # 3. 扩展信号
        self.collect_dragon_tiger()

        print(f"\n{'='*55}")
        print(f"🏁 HTTP采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}")



# ============================================================
# 独立模式 — 不依赖 DataSourceFactory，直接调用 requests
# 适合：mootdx 未安装 / 仅需 HTTP 采集的场景
# ============================================================

class StandaloneHttpCollector:
    """独立HTTP采集器 — 零依赖，直接 requests 采集"""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _save_csv(df: pd.DataFrame, prefix: str) -> str:
        fp = DATA_DIR / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        df.to_csv(fp, index=False, encoding="utf-8-sig")
        return str(fp.name)

    @staticmethod
    def _save_json(data, prefix: str) -> str:
        fp = DATA_DIR / f"{prefix}_{datetime.now():%Y%m%d}.json"
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(fp.name)

    def collect_realtime_tencent(self, codes: list = None) -> pd.DataFrame:
        """腾讯实时行情（纯HTTP，零鉴权）"""
        if codes is None:
            codes = ["000001", "600519", "300750", "002463", "688017"]
        import requests as _req
        codes_str = ",".join(
            f"{'sh' if c.startswith(('6','9')) else 'sz' if c.startswith(('0','3')) else 'bj'}{c}"
            for c in codes
        )
        url = f"https://qt.gtimg.cn/q={codes_str}"
        resp = _req.get(url, timeout=15)
        resp.encoding = "gbk"
        rows = []
        for line in resp.text.strip().split(";"):
            if not line.strip():
                continue
            parts = line.split("~")
            if len(parts) < 46:
                continue
            rows.append({
                "code": parts[2], "name": parts[1],
                "price": float(parts[3] or 0), "change": float(parts[31] or 0),
                "change_pct": float(parts[32] or 0),
                "volume": int(parts[6] or 0), "amount": float(parts[37] or 0),
                "pe_ttm": float(parts[39] or 0), "pb": float(parts[45] or 0),
                "mcap_yi": float(parts[44] or 0), "turnover_pct": float(parts[38] or 0),
            })
        return pd.DataFrame(rows)

    def collect_hot_reason(self, date_str: str = None) -> pd.DataFrame:
        """同花顺热点（纯HTTP）"""
        import requests as _req
        import re as _re
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date_str}/orderby/date/orderway/desc/charset/GBK/"
        resp = _req.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        records = []
        for item in data.get("data", []):
            records.append({
                "名称": item.get("NAME", ""),
                "代码": item.get("CODE", ""),
                "题材归因": item.get("REASON", ""),
                "收盘价": item.get("PRICE", 0),
                "涨幅%": item.get("ZDF", 0),
                "换手率%": item.get("HSL", 0),
                "成交额": item.get("AMOUNT", 0),
                "fetch_date": date_str,
            })
        return pd.DataFrame(records)

    def collect_industry_compare(self, top_n: int = 20) -> dict:
        """行业对比（akshare封装HTTP）"""
        try:
            import akshare as ak
        except ImportError:
            print("  ⚠️  akshare 未安装，跳过行业对比. pip install akshare")
            return {}
        try:
            df = ak.stock_board_industry_name_em()
            if df.empty:
                return {}
            df = df.head(top_n)
            records = []
            for _, row in df.iterrows():
                records.append({
                    "name": row.get("板块名称", ""),
                    "change_pct": float(row.get("涨跌幅", 0)),
                    "turnover_yi": float(row.get("成交额", 0)) / 1e8,
                    "up_count": int(row.get("上涨家数", 0)),
                    "down_count": int(row.get("下跌家数", 0)),
                    "leader": row.get("领涨股票", ""),
                })
            return {"total": len(records), "records": records}
        except Exception as e:
            print(f"  ⚠️  行业对比网络异常(东财反爬): {e}")
            return {}

    def run_all(self):
        print(f"\n{'='*55}")
        print(f"📡 HTTP独立采集 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}\n")

        print(f"[{datetime.now():%H:%M:%S}] 📡 实时行情 (腾讯直连)")
        df = self.collect_realtime_tencent()
        if not df.empty:
            f = self._save_csv(df, "realtime")
            print(f"  ✅ {len(df)} 条 -> {f}")

        print(f"[{datetime.now():%H:%M:%S}] 🔥 题材热点 (同花顺直连)")
        df = self.collect_hot_reason()
        if not df.empty:
            f = self._save_csv(df, "hot_reason")
            print(f"  ✅ {len(df)} 只强势股 -> {f}")

        print(f"[{datetime.now():%H:%M:%S}] 📊 行业对比 (akshare)")
        data = self.collect_industry_compare()
        if data:
            f = self._save_json(data, "industry_compare")
            print(f"  ✅ {data['total']} 个行业 -> {f}")

        print(f"\n{'='*55}")
        print(f"🏁 HTTP独立采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HTTP + TCP 全协议数据采集")
    parser.add_argument("--all", action="store_true", help="全量HTTP采集")
    parser.add_argument("--tcp", action="store_true", help="HTTP + TCP K线采集")
    parser.add_argument("--signals", action="store_true", help="仅采集信号层")
    parser.add_argument("--sync", action="store_true", help="采集后同步MySQL")
    parser.add_argument("--standalone", action="store_true",
                        help="独立模式(零工厂依赖，仅requests+akshare)")
    args = parser.parse_args()

    if args.standalone:
        runner = StandaloneHttpCollector()
        runner.run_all()
    elif args.tcp:
        factory_runner = HttpOnlyCollector()
        factory_runner.collect_tcp_all()
    else:
        factory_runner = HttpOnlyCollector()
        if args.all or args.sync:
            factory_runner.collect_all()
        elif args.signals:
            factory_runner.collect_hot_reason()
            factory_runner.collect_northbound()
            factory_runner.collect_industry_compare()
        else:
            factory_runner.collect_basic()
            factory_runner.collect_realtime()
            factory_runner.collect_hot_reason()
            factory_runner.collect_northbound()
            factory_runner.collect_industry_compare()

    if args.sync:
        print(f"\n📤 同步到MySQL...")
        from sync_to_mysql import main as sync_main
        import sys as _sys
        _sys.argv = [_sys.argv[0]]
        sync_main()

    if args.tcp and args.sync:
        print(f"\n📤 同步K线数据到MySQL...")
        from sync_to_mysql import main as sync_main
        import sys as _sys
        _sys.argv = [_sys.argv[0]]
        sync_main()
