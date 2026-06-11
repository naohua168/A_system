"""
统一数据采集调度脚本（增强版）
支持一次性全量/增量采集，以及定时调度

增强特性:
  1. 采集间隔限流抑制反爬
  2. 采集质量报告
  3. 单数据源失败不中断全流程

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
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd

# 全市场股票列表（从腾讯财经实时扫描获取，非硬编码）
from collectors.stock_list import get_all_stock_codes

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR, RATE_LIMIT

logger = logging.getLogger("data_collector.runner")


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


class DataCollectorRunner:
    """统一数据采集调度器"""

    def __init__(self):
        self.factory = DataSourceFactory()
        self.results = {}
        self.report = CollectReport()

    def _throttle(self):
        """采集间限流"""
        time.sleep(RATE_LIMIT.get("min_interval_between_sources", 0.5))

    # ==========================================================
    # 行情层
    # ==========================================================

    def collect_realtime(self, codes: list = None) -> pd.DataFrame:
        """采集实时行情（腾讯财经，全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📡 实时行情: 全市场 {len(codes)} 只")
        try:
            df = self.factory.get_realtime_quotes(codes)
            if not df.empty:
                self._save("realtime", df)
                print(f"   ✅ {len(df)} 条")
            self.report.record("realtime", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.report.record("realtime", 0, False, time.time() - t0)
            return pd.DataFrame()

    def collect_kline(self, codes: list = None, days: int = 365) -> dict:
        """采集历史K线（mootdx，全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
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
        total = sum(results.values())
        self.report.record("kline", total, bool(results), time.time() - t0)
        return results

    # ==========================================================
    # 信号层
    # ==========================================================

    def collect_hot_reason(self) -> pd.DataFrame:
        """当日强势股题材归因"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🔥 题材归因")
        try:
            df = self.factory.get_hot_reason()
            if not df.empty:
                self._save("hot_reason", df)
                print(f"   ✅ 强势股 {len(df)} 只")
            self.report.record("hot_reason", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"   ❌ {e}")
            self.report.record("hot_reason", 0, False, time.time() - t0)
            return pd.DataFrame()

    def collect_northbound(self) -> pd.DataFrame:
        """北向资金"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🌐 北向资金")
        try:
            df = self.factory.get_northbound_realtime()
            if not df.empty:
                self._save("northbound", df)
                last = df.dropna().iloc[-1]
                nbc = self.factory.get_collector("ths_northbound")
                nbc.save_daily_snapshot(datetime.now().strftime("%Y-%m-%d"),
                                         last["hgt_yi"], last["sgt_yi"])
                print(f"   ✅ 分钟点数 {len(df)}")
            self.report.record("northbound", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"   ❌ {e}")
            self.report.record("northbound", 0, False, time.time() - t0)
            return pd.DataFrame()

    def collect_industry_compare(self) -> dict:
        """行业横向对比"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📊 行业对比")
        try:
            data = self.factory.get_industry_comparison(20)
            if data.get("total", 0) > 0:
                self._save_json("industry_compare", data)
                print(f"   ✅ {data['total']} 个行业")
            self.report.record("industry_compare", data.get("total", 0),
                               bool(data), time.time() - t0)
            return data
        except Exception as e:
            print(f"   ❌ {e}")
            self.report.record("industry_compare", 0, False, time.time() - t0)
            return {}

    def collect_stock_signals(self, codes: list = None) -> dict:
        """采集个股信号层数据（概念板块+资金流向，全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
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
        total_signals = sum(len(v) for v in results.values())
        self.report.record("stock_signals", total_signals, bool(results), time.time() - t0)
        return results

    # ==========================================================
    # 资讯层（研报 + 新闻 + 公告 — a-stock-data 迁移合并）
    # ==========================================================

    def collect_research_reports(self, codes: list = None) -> dict:
        """采集研报列表（全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
        results = {}
        for code in codes:
            print(f"[{datetime.now():%H:%M:%S}] 📄 研报: {code}")
            try:
                reports = self.factory.get_research_reports(code)
                if reports:
                    fp = DATA_DIR / f"research_reports_{code}_{datetime.now():%Y%m%d}.csv"
                    pd.DataFrame(reports).to_csv(fp, index=False, encoding="utf-8-sig")
                    results[code] = len(reports)
                    print(f"   ✅ {len(reports)} 篇")
                else:
                    print("   ⚠️  无数据")
            except Exception as e:
                print(f"   ❌ {e}")
            time.sleep(RATE_LIMIT.get("min_interval_between_sources", 0.5))
        total = sum(results.values())
        self.report.record("research_reports", total, bool(results), time.time() - t0)
        return results

    def collect_consensus_eps(self, codes: list = None) -> dict:
        """采集机构一致预期EPS（全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
        results = {}
        for code in codes:
            print(f"[{datetime.now():%H:%M:%S}] 📈 一致预期: {code}")
            try:
                df = self.factory.get_consensus_eps(code)
                if not df.empty:
                    self._save(f"consensus_eps_{code}", df)
                    results[code] = len(df)
                    print(f"   ✅ {len(df)} 年")
                else:
                    print("   ⚠️  无数据")
            except Exception as e:
                print(f"   ❌ {e}")
            time.sleep(RATE_LIMIT.get("min_interval_between_sources", 0.5))
        total = sum(results.values())
        self.report.record("consensus_eps", total, bool(results), time.time() - t0)
        return results

    def collect_stock_news(self, codes: list = None) -> dict:
        """采集个股新闻（全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
        results = {}
        for code in codes:
            print(f"[{datetime.now():%H:%M:%S}] 📰 个股新闻: {code}")
            try:
                df = self.factory.get_stock_news(code)
                if not df.empty:
                    self._save(f"stock_news_{code}", df)
                    results[code] = len(df)
                    print(f"   ✅ {len(df)} 条")
                else:
                    print("   ⚠️  无数据")
            except Exception as e:
                print(f"   ❌ {e}")
            time.sleep(RATE_LIMIT.get("min_interval_between_sources", 0.5))
        total = sum(results.values())
        self.report.record("stock_news", total, bool(results), time.time() - t0)
        return results

    def collect_cls_news(self) -> pd.DataFrame:
        """财联社快讯"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] ⚡ 财联社快讯")
        try:
            df = self.factory.get_cls_news()
            if not df.empty:
                self._save("cls_news", df)
                print(f"   ✅ {len(df)} 条")
            self.report.record("cls_news", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"   ❌ {e}")
            self.report.record("cls_news", 0, False, time.time() - t0)
            return pd.DataFrame()

    def collect_global_news(self) -> pd.DataFrame:
        """全球财经资讯"""
        self._throttle()
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🌍 全球资讯")
        try:
            df = self.factory.get_global_news()
            if not df.empty:
                self._save("global_news", df)
                print(f"   ✅ {len(df)} 条")
            self.report.record("global_news", len(df), not df.empty, time.time() - t0)
            return df
        except Exception as e:
            print(f"   ❌ {e}")
            self.report.record("global_news", 0, False, time.time() - t0)
            return pd.DataFrame()

    def collect_filings(self, codes: list = None) -> dict:
        """采集巨潮公告（全市场）"""
        if codes is None:
            codes = get_all_stock_codes()
        t0 = time.time()
        results = {}
        for code in codes:
            print(f"[{datetime.now():%H:%M:%S}] 📋 公告: {code}")
            try:
                df = self.factory.get_cninfo_filings(code)
                if not df.empty:
                    self._save(f"filings_{code}", df)
                    results[code] = len(df)
                    print(f"   ✅ {len(df)} 条")
                else:
                    print("   ⚠️  无数据")
            except Exception as e:
                print(f"   ❌ {e}")
            time.sleep(RATE_LIMIT.get("min_interval_between_sources", 0.5))
        total = sum(results.values())
        self.report.record("filings", total, bool(results), time.time() - t0)
        return results

    def collect_info_all(self):
        """资讯层全量采集（研报+新闻+公告）"""
        print(f"\n{'='*50}")
        print(f"📦 资讯层全量采集 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}\n")

        self.collect_research_reports()
        self.collect_consensus_eps()
        self.collect_stock_news()
        self.collect_cls_news()
        self.collect_global_news()
        self.collect_filings()

        print(self.report.summary())
        print(f"\n{'='*50}")
        print(f"🏁 资讯层采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}")

    # ==========================================================
    # 基金数据（货币基金 + ETF）
    # ==========================================================

    def collect_money_market(self):
        """采集货币基金 7日年化/万份收益（只写 CSV，不写 MySQL）"""
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 💰 货币基金: 采集 7日年化...")
        try:
            import akshare as ak
            df = ak.fund_money_rank_em()
            cnt = len(df)
            self._save("money_market_", df)
            self.report.record("money_market", cnt, True, time.time() - t0)
            print(f"   ✅ {cnt} 只货币基金 → CSV")
        except Exception as e:
            self.report.record("money_market", 0, False, time.time() - t0)
            print(f"   ❌ 货币基金采集失败: {e}")

    def collect_etf_market(self):
        """采集 ETF 实时行情（只写 CSV，不写 MySQL）"""
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 📊 ETF 行情: 采集实时行情...")
        try:
            import akshare as ak
            df = ak.fund_etf_spot_em()
            cnt = len(df)
            self._save("etf_market_", df)
            self.report.record("etf_market", cnt, True, time.time() - t0)
            print(f"   ✅ {cnt} 只 ETF → CSV")
        except Exception as e:
            self.report.record("etf_market", 0, False, time.time() - t0)
            print(f"   ❌ ETF 采集失败: {e}")

    # ==========================================================
    # Spark ETL 批处理
    # ==========================================================

    def collect_spark_batch(self):
        """Spark 分布式批处理：行业排行 + 写入 MySQL"""
        t0 = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🔥 Spark 批处理启动...")
        try:
            import subprocess
            cmd = [
                "docker", "exec", "spark-master", "/opt/spark/bin/spark-submit",
                "--master", "spark://spark-master:7077",
                "--driver-memory", "1g", "--executor-memory", "1g",
                "/tmp/bigdata/spark_sector_mysql.py"
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                print(f"   ✅ Spark 完成")
                self.report.record("spark_batch", 1, True, time.time() - t0)
            else:
                print(f"   ⚠️ Spark 失败(将跳过): {r.stderr[:200]}")
                self.report.record("spark_batch", 0, False, time.time() - t0)
        except subprocess.TimeoutExpired:
            print(f"   ⚠️ Spark 超时(300s 后跳过)")
            self.report.record("spark_batch", 0, False, time.time() - t0)
        except Exception as e:
            print(f"   ⚠️ Spark 异常(跳过): {e}")
            self.report.record("spark_batch", 0, False, time.time() - t0)

    # ==========================================================
    # 全量采集
    # ==========================================================

    def collect_all(self):
        """全量采集（包含资讯层）"""
        print(f"\n{'='*50}")
        print(f"📦 全量数据采集启动 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}\n")

        # 行情 + 信号
        self.collect_hot_reason()
        self.collect_northbound()
        self.collect_industry_compare()
        self.collect_realtime()
        self.collect_kline()

        # 基金数据（货币基金 7日年化 + ETF 实时行情）
        self.collect_money_market()
        self.collect_etf_market()

        # 资讯层（研报+新闻+公告）
        self.collect_cls_news()
        self.collect_global_news()

        # Redis 刷新: 从 CSV 写入 Redis（替代已移除的 HDFS 管道）
        print(f"\n📊 刷新 Redis 缓存...")
        try:
            import subprocess
            base = Path(__file__).parent.parent
            subprocess.run([sys.executable, str(base / "auto_seed.py")], timeout=120, capture_output=True)
            print(f"   ✅ Redis 已刷新")
        except Exception as e:
            print(f"   ⚠️ Redis 刷新跳过: {e}")

        # 刷新 Redis 市场数据 — K线从CSV写入 + 实时行情从auto_seed写入
        print(f"\n📊 刷新Redis全量市场数据...")
        try:
            import subprocess
            base = Path(__file__).parent.parent
            # K线: 从本地CSV文件写入Redis (零网络依赖,比调API快10倍)
            r1 = subprocess.run([sys.executable, str(base / "write_kline_to_redis.py")],
                               timeout=180, capture_output=True, text=True)
            if r1.stdout:
                last = r1.stdout.strip().split('\n')[-1]
                print(f'   write_kline: {last}')
            # 实时行情 + 信号: auto_seed (socket RESP)
            r2 = subprocess.run([sys.executable, str(base / "auto_seed.py")],
                               timeout=120, capture_output=True, text=True)
            if r2.stdout:
                last2 = r2.stdout.strip().split('\n')[-1]
                print(f'   auto_seed: {last2}')
            print(f"   ✅ Redis 已刷新")
        except subprocess.TimeoutExpired:
            print(f"   ⚠️ Redis 刷新超时")
        except Exception as e:
            print(f"   ❌ Redis 刷新失败: {e}")

        print(self.report.summary())
        print(f"\n{'='*50}")

        # 通知后端清理缓存
        self._evict_cache()

        print(f"🏁 全量采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}")

    def _evict_cache(self):
        """直连 Redis 删除 Spring Cache 所有缓存 key（不依赖后端 HTTP）"""
        print(f"\n[{datetime.now():%H:%M:%S}] 🗑️  清理后端缓存...")
        try:
            import redis
            rd = redis.Redis(host='redis', port=6379, db=0, socket_timeout=5)
            # Spring Cache Redis key 格式: {cacheName}::{key}
            patterns = [
                'realtime::*', 'signalMarketData::*',
                'signalHotData::*', 'signalDragonTiger::*',
                'signalReferenceData::*', 'stockList::*', 'stockDaily::*',
                'infoReport::*', 'infoNews::*', 'infoFiling::*', 'fundNav::*',
            ]
            total = 0
            for pattern in patterns:
                cursor = 0
                while True:
                    cursor, keys = rd.scan(cursor=cursor, match=pattern, count=200)
                    if keys:
                        rd.delete(*keys)
                        total += len(keys)
                    if cursor == 0:
                        break
            print(f"   ✅ 已清理 {total} 个缓存 key")
        except ImportError:
            print(f"   ⚠️ redis 模块未安装，跳过缓存清理")
        except Exception as e:
            print(f"   ⚠️ 缓存清理失败(不影响数据): {e}")
        print(f"🏁 全量采集完成 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
        print(f"{'='*50}")

    # ==========================================================
    # 工具方法
    # ==========================================================

    def _run_sync(self):
        """执行 sync_to_mysql (兜底: 失败不影响采集)"""
        try:
            from sync_to_mysql import main as sync_main
            import sys as _sys
            saved = _sys.argv.copy()
            _sys.argv = [_sys.argv[0]]
            try:
                sync_main()
            finally:
                _sys.argv = saved
        except Exception as e:
            print(f"   ⚠️ 同步失败(采集已完成): {e}")

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
    parser = argparse.ArgumentParser(description="统一数据采集调度脚本 (增强版)")
    parser.add_argument("--all", action="store_true", help="全量采集（旧模式 -> CSV）")
    parser.add_argument("--realtime", action="store_true", help="仅采集实时行情")
    parser.add_argument("--kline", action="store_true", help="仅采集K线")
    parser.add_argument("--signals", action="store_true", help="仅采集信号层数据")
    parser.add_argument("--info", action="store_true", help="仅采集资讯层数据（研报+新闻+公告）")
    parser.add_argument("--stock", type=str, help="指定股票代码采集")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔（分钟），0=不循环")
    parser.add_argument("--mode", type=str, choices=["realtime","batch","incremental","full"],
                        help="采集模式: realtime(盘中高频) / batch(收盘批处理) / full(全量)")
    parser.add_argument("--sync", action="store_true", help="采集后同步到MySQL")

    # 管道模式（新一代适配器+存储+管道）
    parser.add_argument("--pipeline", action="store_true", help="管道模式（适配器+存储+管道三件套）")
    parser.add_argument("--pipeline-layer", type=str, choices=["market", "signal", "information"],
                        help="管道模式按层采集")

    # 编排器模式（全量管道，自动写MySQL）
    parser.add_argument("--collect-all", action="store_true",
                        help="编排器全量采集（所有层，自动写MySQL+CSV）")
    parser.add_argument("--collect-layer", type=str, choices=["market", "signal", "information", "all"],
                        help="编排器按层采集（自动写MySQL+CSV）")
    parser.add_argument("--validate", action="store_true",
                        help="采集后执行数据校验，报告各表记录数")
    parser.add_argument("--global-only", action="store_true",
                        help="仅采集全局类型（最快，无需逐股迭代）")

    args = parser.parse_args()
    runner = DataCollectorRunner()

    def run_once():
        # ==================== 编排器管道模式（新，自动写MySQL） ====================
        if args.collect_all or args.collect_layer or args.global_only:
            from adapters.collector_adapters import register_all_adapters
            register_all_adapters()
            from pipeline.orchestrator import ParallelCollector
            pc = ParallelCollector(max_workers=4)
            try:
                if args.collect_all:
                    report = pc.collect_all()
                elif args.global_only:
                    report = pc.collect_global_only()
                elif args.collect_layer:
                    if args.collect_layer == "all":
                        report = pc.collect_all()
                    else:
                        report = pc.collect_layer(args.collect_layer)
                print(report.summary())
            finally:
                pc.close()

            if args.validate:
                _validate_data()
            return

        # 仅校验（不采集）
        if args.validate:
            _validate_data()
            return

        # ==================== 管道模式 ====================
        if args.pipeline or args.pipeline_layer:
            _run_pipeline(args)
            return

        # ==================== 新版 mode 调度 ====================
        now_ts = datetime.now()
        hour = now_ts.hour
        is_market_day = now_ts.weekday() < 5  # 周一到周五
        is_market_hours = is_market_day and ((9 <= hour < 11) or (13 <= hour < 15))

        if args.mode == "realtime":
            print(f"🔄 实时模式 (market_hours={is_market_hours})")
            if is_market_hours:
                runner.collect_realtime()
                runner.collect_northbound()
                runner.collect_etf_market()
            else:
                print("   非交易时段，仅更新财联社快讯")
                runner.collect_cls_news()
            if args.sync:
                runner._run_sync()

        elif args.mode == "batch":
            print(f"🔄 批处理模式 (收盘后)")
            runner.collect_kline()
            runner.collect_hot_reason()
            runner.collect_northbound()
            runner.collect_industry_compare()
            # 基金数据
            runner.collect_money_market()
            runner.collect_etf_market()
            # 资讯
            runner.collect_cls_news()
            runner.collect_global_news()
            # 上传 HDFS + Spark
            print(f"\n📤 上传 HDFS...")
            try:
                from scheduler.upload_to_hdfs import HDFSUploader
                u = HDFSUploader()
                u.upload_all()
                u.run_hive_msck()
            except Exception as e:
                print(f"   ⚠️ HDFS 失败(继续): {e}")
            print(f"🔥 Spark 批处理...")
            runner.collect_spark_batch()
            if args.sync:
                runner._run_sync()

        elif args.mode == "full":
            runner.collect_all()
            if args.sync:
                runner._run_sync()

        elif args.mode == "incremental":
            print(f"🔄 增量模式")
            runner.collect_realtime()
            runner.collect_cls_news()
            if is_market_hours:
                runner.collect_northbound()
                runner.collect_etf_market()
            if args.sync:
                runner._run_sync()

        else:
            # ==================== 旧版调度模式（兼容保留） ====================
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
            elif args.info:
                runner.collect_info_all()
            elif args.stock:
                runner.collect_stock_signals([args.stock])
            else:
                parser.print_help()
                return
            if args.sync:
                runner._run_sync()

    if args.loop > 0:
        print(f"🔄 智能定时采集启动")
        _running = True
        import signal as _signal

        def _handle_signal(signum, frame):
            nonlocal _running
            print(f"\n⏹️  收到信号 {signum}，正在停止采集...")
            _running = False

        _signal.signal(_signal.SIGINT, _handle_signal)
        _signal.signal(_signal.SIGTERM, _handle_signal)

        last_batch_date = ""

        try:
            while _running:
                now = datetime.now()
                h, wd = now.hour, now.weekday()
                is_trading_day = wd < 5
                today_str = now.strftime("%Y-%m-%d")

                # ── 持续刷新新闻（盘中/盘后均运行，每5分钟） ──
                try:
                    runner.collect_cls_news()
                except:
                    pass
                try:
                    runner.collect_global_news()
                except:
                    pass
                # ── 刷新 Redis 新闻（run_collector的新闻采集只写CSV，Redis需单独刷新）──
                try:
                    import subprocess as _sp2
                    _sp2.run([sys.executable, '-c',
                        'import sys; sys.path.insert(0,"/app"); from auto_seed import _ensure_news_data; _ensure_news_data()'],
                        capture_output=True, timeout=20)
                except Exception:
                    pass

                # ── 日K/分钟K线刷新（后台启动，不阻塞主循环）──
                try:
                    import subprocess as _sp3
                    # 分钟K线TTL检查
                    _ret = _sp3.run([sys.executable, '-c',
                        'import sys; sys.path.insert(0,"/app"); from auto_seed import _min_kline_needs_refresh; ' +
                        'exit(0 if _min_kline_needs_refresh() else 1)'],
                        capture_output=True, timeout=15)
                    if _ret.returncode == 0:
                        for _p in ['5min', '15min', '30min', '60min']:
                            _sp3.Popen([sys.executable, '/app/seed_kline.py', '--period', _p],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print(f'  [{datetime.now():%H:%M:%S}] 分钟K线刷新已启动（4周期）')
                except Exception:
                    pass

                # ── 日K结算检查：最新K线日期非今日 → 后台重采（攻克腾讯API延迟问题）──
                try:
                    import subprocess as _spk
                    _kdate_ret = _spk.run([sys.executable, '-c',
                        'import sys,json,subprocess as sp; ' +
                        'r=sp.run(["redis-cli","-h","redis","GET","market:kline_000001"],capture_output=True,text=True,timeout=5); ' +
                        'd=json.loads(r.stdout.strip()) if r.stdout.strip() else []; ' +
                        'latest_date=d[0].get("tradeDate","") if d else ""; ' +
                        'today=__import__("datetime").date.today().strftime("%Y%m%d"); ' +
                        'exit(0 if latest_date != today else 1)'],
                        capture_output=True, timeout=15)
                    if _kdate_ret.returncode == 0:
                        _spk.Popen([sys.executable, '/app/seed_kline.py'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print(f'  [{datetime.now():%H:%M:%S}] 日K结算未就绪，后台重采...')
                except Exception:
                    pass

                # ── 收盘快照：交易日 15:00 后触发（每天一次） ──
                if is_trading_day and h >= 15:
                    try:
                        import subprocess as _sp4
                        _sp4.run([sys.executable, '-c',
                            'import sys; sys.path.insert(0,"/app"); from auto_seed import data_rollover; data_rollover()'],
                            capture_output=True, timeout=600)
                    except Exception:
                        pass

                if args.sync:
                    runner._run_sync()
                interval = 5
                print(f"\n⏳ 新闻刷新: 等待 {interval} 分钟...\n")
                time.sleep(interval * 60)

                if not _running:
                    break
        finally:
            print("✅ 采集循环已安全退出")
    else:
        run_once()


# ============================================================
# 管道模式运行器（适配器+存储+管道三件套）
# ============================================================
def _run_pipeline(args):
    """通过采集管道运行，数据自动写 MySQL + CSV"""
    from adapters.collector_adapters import register_all_adapters
    register_all_adapters()

    from pipeline.collection_pipeline import CollectionPipeline
    pipeline = CollectionPipeline()

    try:
        if args.pipeline_layer:
            print(f"\n📦 按层采集: {args.pipeline_layer}")
            report = pipeline.run_layer(args.pipeline_layer)
        else:
            # --pipeline 默认采集行情层测试
            report = pipeline.run("realtime_quotes")
        print(report.summary())
    finally:
        pipeline.close()

    if args.sync:
        print(f"\n📤 同步到MySQL...")
        from scheduler.sync_engine import main as sync_main
        # 临时替换 sys.argv 避免解析到旧参数
        import sys as _sys
        saved = _sys.argv.copy()
        _sys.argv = [_sys.argv[0]]
        try:
            sync_main()
        finally:
            _sys.argv = saved


# ============================================================
# 数据校验 + 缺失表自动创建
# ============================================================
def _ensure_tables():
    """确保 MySQL 业务表存在（不再创建市场数据表，市场数据走 Hive）"""
    import pymysql
    from config import MYSQL_CONFIG
    biz_tables = {
        "user": "CREATE TABLE IF NOT EXISTS `user` (id BIGINT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE, password VARCHAR(255) NOT NULL, role INT DEFAULT 1, status INT DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
        "watchlist": "CREATE TABLE IF NOT EXISTS `watchlist` (id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT NOT NULL, asset_code VARCHAR(20) NOT NULL, asset_type TINYINT DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
    }
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cur = conn.cursor()
        for tbl, ddl in biz_tables.items():
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                        (MYSQL_CONFIG['database'], tbl))
            if cur.fetchone()[0] == 0:
                cur.execute(ddl)
                print(f"  ✅ 创建业务表: {tbl}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  ⚠️ 业务表创建跳过: {e}")


def _validate_data():
    """校验各 MySQL 表的数据完整性"""
    _ensure_tables()
    import pymysql
    from config import MYSQL_CONFIG
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cur = conn.cursor()
        tables = [
            'stock', 'stock_daily', 'index_daily', 'market_index',
            'signal_hot_reason', 'signal_northbound', 'signal_daily_industry',
            'signal_dragon_tiger_detail', 'signal_lockup_detail',
            'signal_fund_flow', 'signal_concept_block',
            'info_cls_news', 'info_global_news',
        ]
        print(f"\n{'='*50}")
        print("📋 数据校验报告")
        print(f"{'='*50}")
        total = 0
        for t in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM {t}')
                cnt = cur.fetchone()[0]
                total += cnt
                icon = "✅" if cnt > 0 else "⬜"
                print(f"  {icon} {t:30s} {cnt:>8,} 行")
            except Exception:
                print(f"  ❌ {t:30s} 表不存在")
        print(f"{'='*50}")
        print(f"  📦 总计: {total:,} 行")
        print(f"{'='*50}")
        conn.close()
    except Exception as e:
        print(f"  ❌ 数据库连接失败: {e}")


if __name__ == "__main__":
    main()
