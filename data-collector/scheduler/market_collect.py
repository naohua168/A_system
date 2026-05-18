"""
HTTP + TCP 全协议数据采集脚本（增强版）
支持6个数据源（5个HTTP直连 + 1个TCP通达信）：

  采集器          | 协议  | 数据类型
  ─────────────────┼───────┼──────────────────────────────
  tencent         | HTTP  | 实时行情+PE/PB/市值/换手率
  ths_hot         | HTTP  | 强势股题材归因+热点
  ths_northbound  | HTTP  | 北向资金实时分钟流向
  baidu           | HTTP  | 概念板块+个股资金流向
  akshare_ext     | HTTP  | 龙虎榜/解禁/行业对比/研报/公告
  mootdx          | TCP   | K线(多周期)/五档盘口/逐笔成交/财务快照/F10

增强特性:
  1. 采集间隔限流（避免反爬）
  2. 采集结束生成数据质量报告
  3. 修复 --sync 重复调用的 bug
  4. 异常降级: 单数据源失败不阻塞全流程

用法:
    python market_collect.py                    # HTTP全量采集(默认)
    python market_collect.py --tcp              # HTTP + TCP K线采集
    python market_collect.py --standalone       # 独立模式(零工厂依赖)
    python market_collect.py --sync             # HTTP采集+同步MySQL
"""
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR, RATE_LIMIT

logger = logging.getLogger("data_collector.market")

# ============================================================
# 全市场股票列表（从腾讯财经实时扫描获取，非硬编码）
# ============================================================
from collectors.stock_list import get_all_stock_codes
FULL_MARKET_CODES = get_all_stock_codes()  # ~5500 只


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class CollectReport:
    """采集质量报告"""

    def __init__(self):
        self.collectors = {}

    def record(self, name: str, rows: int, success: bool, elapsed: float):
        self.collectors[name] = {
            "rows": rows,
            "success": success,
            "elapsed_s": round(elapsed, 2),
        }

    def summary(self) -> str:
        lines = [f"\n{'='*50}", "📊 采集质量报告", f"{'='*50}"]
        total_ok = sum(1 for v in self.collectors.values() if v["success"])
        total_rows = sum(v["rows"] for v in self.collectors.values())
        lines.append(f"  成功: {total_ok}/{len(self.collectors)}  总行数: {total_rows}")
        lines.append(f"{'-'*50}")
        for name, info in self.collectors.items():
            icon = "✅" if info["success"] else "❌"
            lines.append(f"  {icon} {name:20s}  {info['rows']:>6}行  {info['elapsed_s']:>6.2f}s")
        lines.append(f"{'='*50}")
        return "\n".join(lines)


class HttpOnlyCollector:
    """HTTP专属采集器 — 仅使用HTTP直连数据源"""

    def __init__(self):
        self.factory = DataSourceFactory()
        self.results = {}
        self.report = CollectReport()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _throttle(self, seconds: float = None):
        """采集间隔限流"""
        sec = seconds if seconds is not None else RATE_LIMIT.get("min_interval_between_sources", 0.5)
        time.sleep(sec)

    # ----------------------------------------------------------
    # 1. 实时行情（腾讯财经 HTTP）
    # ----------------------------------------------------------
    def collect_realtime(self, codes: list = None) -> pd.DataFrame:
        """采集实时行情 + PE/PB/市值"""
        if codes is None:
            codes = TEST_CODES
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📡 实时行情 (腾讯) codes={len(codes)}")
        try:
            df = self.factory.get_realtime_quotes(codes)
            if not df.empty:
                fp = DATA_DIR / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 条 -> {fp.name}")
            else:
                print("  ⚠️  空数据")
            self.report.record("realtime", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"  ❌ {e}")
            self.report.record("realtime", 0, False, time.time() - t0)
            return pd.DataFrame()

    # ----------------------------------------------------------
    # 2. 股票基本信息（腾讯财经 HTTP）
    # ----------------------------------------------------------
    def collect_basic(self, codes: list = None) -> pd.DataFrame:
        """采集股票基本信息"""
        if codes is None:
            codes = TEST_CODES
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📋 股票基本信息 (腾讯)")
        try:
            df = self.factory.get_stock_basic(codes)
            if not df.empty:
                fp = DATA_DIR / f"stock_basic_{datetime.now():%Y%m%d}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 只 -> {fp.name}")
            else:
                print("  ⚠️  空数据")
            self.report.record("stock_basic", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"  ❌ {e}")
            self.report.record("stock_basic", 0, False, time.time() - t0)
            return pd.DataFrame()

    # ----------------------------------------------------------
    # 3. 题材热点（同花顺 HTTP）
    # ----------------------------------------------------------
    def collect_hot_reason(self) -> pd.DataFrame:
        """当日强势股题材归因"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🔥 题材归因 (同花顺)")
        try:
            df = self.factory.get_hot_reason()
            if not df.empty:
                fp = DATA_DIR / f"hot_reason_{datetime.now():%Y%m%d}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 只强势股 -> {fp.name}")
                self.report.record("hot_reason", len(df), True, time.time() - t0)
                return df
        except Exception as e:
            print(f"  ❌ {e}")
        self.report.record("hot_reason", 0, False, time.time() - t0)
        return pd.DataFrame()

    # ----------------------------------------------------------
    # 4. 北向资金（同花顺 HTTP）
    # ----------------------------------------------------------
    def collect_northbound(self) -> pd.DataFrame:
        """北向资金实时分钟流向"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🌐 北向资金 (同花顺)")
        try:
            df = self.factory.get_northbound_realtime()
            if not df.empty:
                fp = DATA_DIR / f"northbound_{datetime.now():%Y%m%d}.csv"
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"  ✅ {len(df)} 分钟数据 -> {fp.name}")
                self.report.record("northbound", len(df), True, time.time() - t0)
                return df
        except Exception as e:
            print(f"  ❌ {e}")
        self.report.record("northbound", 0, False, time.time() - t0)
        return pd.DataFrame()

    # ----------------------------------------------------------
    # 5. 行业对比（akshare HTTP）
    # ----------------------------------------------------------
    def collect_industry_compare(self) -> dict:
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📊 行业对比 (akshare)")
        try:
            data = self.factory.get_industry_comparison(20)
            if data.get("total", 0) > 0:
                fp = DATA_DIR / f"industry_compare_{datetime.now():%Y%m%d}.json"
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  ✅ {data['total']} 个行业 -> {fp.name}")
                self.report.record("industry_compare", data["total"], True, time.time() - t0)
                return data
        except Exception as e:
            print(f"  ❌ {e}")
        self.report.record("industry_compare", 0, False, time.time() - t0)
        return {}

    # ----------------------------------------------------------
    # 6. 概念板块（百度 HTTP）
    # ----------------------------------------------------------
    def collect_concept_blocks(self, codes: list = None) -> dict:
        if codes is None:
            codes = TEST_CODES[:3]
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🏷️  概念板块 (百度)")
        results = {}
        for code in codes:
            try:
                data = self.factory.get_concept_blocks(code)
                results[code] = data
                print(f"  {code}: 行业{len(data.get('industry',[]))} 概念{len(data.get('concept_tags',[]))}个")
            except Exception as e:
                print(f"  {code}: ❌ {e}")
            time.sleep(RATE_LIMIT.get("concept_blocks_interval", 0.3))
        fp = DATA_DIR / f"concept_blocks_{datetime.now():%Y%m%d}.json"
        fp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        total_tags = sum(len(v.get("concept_tags", [])) if isinstance(v, dict) else 0 for v in results.values())
        self.report.record("concept_blocks", total_tags, bool(results), time.time() - t0)
        return results

    # ----------------------------------------------------------
    # 7. 个股资金流向（百度 HTTP）
    # ----------------------------------------------------------
    def collect_fund_flow(self, codes: list = None, days: int = 10) -> dict:
        if codes is None:
            codes = TEST_CODES[:3]
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 💧 资金流向 (百度)")
        results = {}
        for code in codes:
            try:
                history = self.factory.get_fund_flow_history(code, days)
                results[code] = {"days": len(history), "data": history[:3]}
                print(f"  {code}: {len(history)} 日")
            except Exception as e:
                print(f"  {code}: ❌ {e}")
            time.sleep(RATE_LIMIT.get("fund_flow_interval", 0.3))
        fp = DATA_DIR / f"fund_flow_{datetime.now():%Y%m%d}.json"
        fp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        total_days = sum(v.get("days", 0) if isinstance(v, dict) else 0 for v in results.values())
        self.report.record("fund_flow", total_days, bool(results), time.time() - t0)
        return results

    # ----------------------------------------------------------
    # 8. 龙虎榜（akshare HTTP）
    # ----------------------------------------------------------
    def collect_dragon_tiger(self, trade_date: str = None) -> dict:
        self._throttle(RATE_LIMIT.get("dragon_tiger_interval", 1.0))
        t0 = time.time()
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
                self.report.record("dragon_tiger", data["total_records"], True, time.time() - t0)
                return data
        except Exception as e:
            print(f"  ❌ {e}")
        self.report.record("dragon_tiger", 0, False, time.time() - t0)
        return {}

    # ----------------------------------------------------------
    # 9. TCP K线（mootdx — 通达信 TCP 7709端口）
    # ----------------------------------------------------------
    def collect_kline(self, codes: list = None, years: int = 2) -> dict:
        """通过 mootdx TCP 采集历史K线数据"""
        if codes is None:
            codes = TEST_CODES
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📈 TCP K线 (mootdx) codes={len(codes)}")
        results = {}
        try:
            collector = self.factory.get_collector("mootdx")
        except Exception as e:
            print(f"  ❌ mootdx 不可用: {e}（pip install mootdx 或检查国内IP）")
            self.report.record("kline", 0, False, time.time() - t0)
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
        total_kline = sum(results.values())
        self.report.record("kline", total_kline, bool(results), time.time() - t0)
        return results

    # ----------------------------------------------------------
    # TCP全量采集（K线 + 实时行情）
    # ----------------------------------------------------------
    def collect_tcp_all(self):
        print(f"\n{'='*55}")
        print(f"📡 HTTP + TCP 全量采集 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*55}\n")

        self.collect_basic()
        self._throttle()
        self.collect_realtime()
        self.collect_hot_reason()
        self.collect_northbound()
        self.collect_industry_compare()
        self.collect_kline()

        print(self.report.summary())
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
        self._throttle()
        self.collect_realtime()

        # 2. 信号层
        self.collect_hot_reason()
        self.collect_northbound()
        self.collect_industry_compare()
        self.collect_concept_blocks()
        self.collect_fund_flow()

        # 3. 扩展信号
        self.collect_dragon_tiger()

        print(self.report.summary())
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
        self.report = CollectReport()
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
        """腾讯实时行情（纯HTTP，零鉴权，全市场）"""
        if codes is None:
            codes = FULL_MARKET_CODES
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
                "price": _safe_float(parts[3]), "change": _safe_float(parts[31]),
                "change_pct": _safe_float(parts[32]),
                "volume": int(parts[6] or 0), "amount": _safe_float(parts[37]),
                "pe_ttm": _safe_float(parts[39]), "pb": _safe_float(parts[45]),
                "mcap_yi": _safe_float(parts[44]), "turnover_pct": _safe_float(parts[38]),
            })
        return pd.DataFrame(rows)

    def collect_hot_reason(self, date_str: str = None) -> pd.DataFrame:
        """同花顺热点（纯HTTP）"""
        import requests as _req
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        url = (f"http://zx.10jqka.com.cn/event/api/getharden/date/{date_str}"
               f"/orderby/date/orderway/desc/charset/GBK/")
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
                    "change_pct": _safe_float(row.get("涨跌幅", 0)),
                    "turnover_yi": _safe_float(row.get("成交额", 0)) / 1e8,
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
    parser = argparse.ArgumentParser(description="HTTP + TCP 全协议数据采集 (增强版)")
    parser.add_argument("--all", action="store_true", help="全量HTTP采集")
    parser.add_argument("--tcp", action="store_true", help="HTTP + TCP K线采集")
    parser.add_argument("--signals", action="store_true", help="仅采集信号层")
    parser.add_argument("--sync", action="store_true", help="采集后同步MySQL")
    parser.add_argument("--standalone", action="store_true",
                        help="独立模式(零工厂依赖，仅requests+akshare)")
    args = parser.parse_args()

    factory_runner = None
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

    # 修复: 使用 sync_once 标志防止重复调用
    if factory_runner is not None:
        sync_done = getattr(factory_runner, '_sync_done', False)
        if args.sync and not sync_done:
            print(f"\n📤 同步到MySQL...")
            from sync_to_mysql import main as sync_main
            import sys as _sys
            saved_argv = _sys.argv.copy()
            _sys.argv = [_sys.argv[0]]
            try:
                sync_main()
            finally:
                _sys.argv = saved_argv
            factory_runner._sync_done = True
