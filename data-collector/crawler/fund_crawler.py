"""
基金数据采集入口（全量升级版）
采集流程: 东方财富(akshare/HTTP) → CSV → MySQL

功能:
  1. fetch_all_funds — 采集全量开放式基金列表（约 10000+ 只）
  2. fetch_fund_detail — 采集单只基金详细信息（公司/经理/规模/类型）
  3. fetch_nav — 采集基金净值历史
  4. fetch_holdings — 采集基金前十大持仓

用法:
    python fund_crawler.py all                    # 全量基金列表 + 详情
    python fund_crawler.py detail 000001          # 单只基金详情
    python fund_crawler.py nav 000001 --days 365  # 净值历史
    python fund_crawler.py holdings 000001        # 持仓
    python fund_crawler.py sync                   # 同步 CSV → MySQL
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from collectors.data_source_factory import DataSourceFactory
from config import DATA_DIR

logger = logging.getLogger(__name__)

# ── 东方财富基金 datacenter API ──
EASTMONEY_FUND_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EASTMONEY_FUND_DETAIL_URL = "https://fundgz.1234567.com.cn/js/{code}.js"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/",
}


class FundCrawler:
    """基金数据全量采集器"""

    def __init__(self):
        self.factory = DataSourceFactory()
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    # ──────────────────────────────────────────────
    # 1. 全量基金列表（通过 akshare 获取）
    # ──────────────────────────────────────────────
    def fetch_all_funds(self, save: bool = True) -> pd.DataFrame:
        """采集全量开放式基金基础信息（通过 akshare 东方财富源）"""
        print("📋 采集全量开放式基金列表...")
        try:
            import akshare as ak
            # 获取所有基金代码和名称
            df_name = ak.fund_name_em()
            print(f"  基金名称表: {len(df_name)} 只")
            # 获取开放式基金排行（含更多字段）
            df_rank = ak.fund_open_fund_rank_em()
            print(f"  基金排行: {len(df_rank)} 只")
        except Exception as e:
            logger.error("akshare 基金列表采集失败: %s", e)
            return pd.DataFrame()

        # 合并数据：以 fund_em_fund_name 为全量基础
        # fund_em_fund_name 字段: 基金代码, 基金简称, 基金类型, 基金拼音全称
        # fund_em_open_fund_rank 字段: 基金代码, 基金简称, 单位净值, 累计净值, 日增长率,
        #   近1周, 近1月, 近3月, 近6月, 近1年, 近2年, 近3年, 今年来, 成立来, 成立日期, 基金类型, 手续费

        rank_map = {}
        if not df_rank.empty:
            rank_col = "基金代码" if "基金代码" in df_rank.columns else df_rank.columns[0]
            for _, r in df_rank.iterrows():
                code = str(r[rank_col])
                rank_map[code] = r.to_dict()

        name_col = "基金代码" if "基金代码" in df_name.columns else df_name.columns[0]
        type_col = "基金类型" if "基金类型" in df_name.columns else None
        name_col2 = "基金简称" if "基金简称" in df_name.columns else df_name.columns[1]
        records = []
        for _, row in df_name.iterrows():
            code = str(row[name_col])
            detail = rank_map.get(code, {})
            records.append({
                "fund_code": code,
                "fund_name": str(row.get(name_col2, "")),
                "fund_type": str(detail.get("基金类型", row.get(type_col, "")) if detail else row.get(type_col, "")),
                "company": "",
                "manager": "",
                "establish_date": str(detail.get("成立日期", ""))[:10] if detail else "",
                "nav": float(detail.get("单位净值", 0)) if detail else 0,
                "accumulated_nav": float(detail.get("累计净值", 0)) if detail else 0,
                "scale": 0,
                "status": 1,
            })
        df = pd.DataFrame(records)
        print(f"✅ 共采集 {len(df)} 只基金")

        if save:
            fp = str(DATA_DIR / f"fund_basic_{datetime.now():%Y%m%d_%H%M%S}.csv")
            df.to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {fp}")
        return df

    # ──────────────────────────────────────────────
    # 2. 基金详情（东方财富基金概况页面）
    # ──────────────────────────────────────────────
    def fetch_fund_detail(self, code: str, save: bool = True) -> dict:
        """采集单只基金详细信息"""
        print(f"📊 采集基金详情: {code}")

        # 使用东方财富基金详情 API（代码需 6 位零填充）
        padded_code = code.zfill(6)
        url = f"https://fund.eastmoney.com/pingzhongdata/{padded_code}.js"
        try:
            r = self._session.get(url, timeout=15)
            text = r.text
        except Exception as e:
            logger.error("基金详情请求失败 [%s]: %s", code, e)
            return {}

        result = {"fund_code": code}

        # 从 JavaScript 变量中解析关键字段
        try:
            import json
            # 基金经理 (数组: [{"name": "郑晓辉", ...}])
            mgr_raw = self._extract_js_var(text, "Data_currentFundManager")
            if mgr_raw:
                mgrs = json.loads(mgr_raw)
                if mgrs:
                    result["manager"] = mgrs[0].get("name", "")
            # 基金规模 (对象: {"series":[{"y":26.0},...]})
            scale_raw = self._extract_js_var(text, "Data_fluctuationScale")
            if scale_raw:
                scale_obj = json.loads(scale_raw)
                series = scale_obj.get("series", [])
                if series:
                    result["scale"] = float(series[-1].get("y", 0))
        except Exception as e:
            logger.warning("基金详情解析失败 [%s]: %s", code, e)

        if result.get("manager") or result.get("scale"):
            print(f"  基金: {code} | 经理: {result.get('manager', '--')} | 规模: {result.get('scale', '--')}亿")
        else:
            print(f"  基金: {code} | 无详情数据")

        if save and (result.get("manager") or result.get("scale")):
            fp = str(DATA_DIR / f"fund_detail_{code}_{datetime.now():%Y%m%d}.csv")
            pd.DataFrame([result]).to_csv(fp, index=False, encoding="utf-8-sig")
        return result

    @staticmethod
    def _extract_js_var(text: str, var_name: str) -> str:
        """从 JS 中提取变量值（括号计数法，支持嵌套 JSON）"""
        idx = text.find(var_name + " =")
        if idx < 0:
            idx = text.find(var_name + "=")
        if idx < 0:
            return ""
        start = text.index("=", idx) + 1
        while start < len(text) and text[start] in " \t":
            start += 1
        if start >= len(text):
            return ""
        brace = text[start]
        if brace in ("[", "{"):
            open_b, close_b = ("[", "]") if brace == "[" else ("{", "}")
            depth = 0
            end = start
            while end < len(text):
                ch = text[end]
                if ch == "\\":
                    end += 2; continue
                if ch == open_b:
                    depth += 1
                elif ch == close_b:
                    depth -= 1
                    if depth == 0:
                        return text[start:end + 1]
                elif ch in "\"'":
                    q = ch; end += 1
                    while end < len(text) and text[end] != q:
                        if text[end] == "\\": end += 1
                        end += 1
                end += 1
            return text[start:end]
        # 简单值（字符串/数值）
        if brace in "\"'":
            q = brace; end = start + 1
            while end < len(text) and text[end] != q:
                if text[end] == "\\": end += 1
                end += 1
            return text[start:end + 1]
        import re
        m = re.search(r"(-?[\d.]+)", text[start:])
        return text[start:start + m.end()] if m else ""

# ──────────────────────────────────────────────
# 3. 批量采集基金详情（多线程加速）
# ──────────────────────────────────────────────
    def batch_fetch_details(self, codes: list, save: bool = True, threads: int = 8):
        """批量采集基金详情（多线程）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        total = len(codes)
        print(f"📋 批量采集 {total} 只基金详情 (并发 {threads} 线程)...")
        results = [None] * total

        def fetch_one(i, code):
            try:
                detail = self.fetch_fund_detail(code, save=False)
                return i, detail
            except Exception as e:
                logger.warning("采集失败 [%s]: %s", code, e)
                return i, None

        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {pool.submit(fetch_one, i, c): i for i, c in enumerate(codes)}
            done = 0
            for f in as_completed(futures):
                done += 1
                if done % 100 == 0 or done == total:
                    print(f"  进度: {done}/{total}")
                i, detail = f.result()
                results[i] = detail

        results = [r for r in results if r]
        df = pd.DataFrame(results)
        if save and not df.empty:
            fp = str(DATA_DIR / f"fund_details_{datetime.now():%Y%m%d_%H%M%S}.csv")
            df.to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 批量详情已保存: {fp} ({len(df)} 条)")
        return df

    # ──────────────────────────────────────────────
    # 4. 基金净值历史
    # ──────────────────────────────────────────────
    def fetch_nav(self, code: str, days: int = 365, save: bool = True) -> pd.DataFrame:
        """采集基金净值"""
        end = datetime.now()
        start = end - timedelta(days=days)
        print(f"📊 采集基金净值: {code}  {start:%Y%m%d}~{end:%Y%m%d}")

        collector = self.factory.get_collector("akshare_ext")
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
            fp = str(DATA_DIR / f"fund_nav_{code}_{end:%Y%m%d}.csv")
            df.to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {fp}")
        return df

    # ──────────────────────────────────────────────
    # 5. 基金持仓
    # ──────────────────────────────────────────────
    def fetch_holdings(self, code: str, save: bool = True) -> pd.DataFrame:
        """采集基金前十大持仓"""
        print(f"🏢 采集基金持仓: {code}")
        collector = self.factory.get_collector("akshare_ext")
        try:
            df = collector.fetch_fund_holdings(code)
            if df.empty:
                print("⚠️  未获取到持仓数据")
                return df
            print(f"✅ 获取到 {len(df)} 条持仓记录")
            if save:
                fp = str(DATA_DIR / f"fund_holding_{code}_{datetime.now():%Y%m%d_%H%M%S}.csv")
                df.to_csv(fp, index=False, encoding="utf-8-sig")
                print(f"💾 已保存: {fp}")
            return df
        except Exception as e:
            logger.error("持仓采集失败 [%s]: %s", code, e)
            return pd.DataFrame()

    # ──────────────────────────────────────────────
    # 6. MySQL 连接（用于 details 命令）
    # ──────────────────────────────────────────────
    def _get_mysql_conn(self):
        """获取 MySQL 连接"""
        import pymysql
        return pymysql.connect(
            host="mysql",
            port=3306,
            user="root",
            password="hadoop123",
            database="stock_analysis",
            charset="utf8mb4",
        )


def main():
    parser = argparse.ArgumentParser(description="📊 基金数据采集器 v2")
    sub = parser.add_subparsers(dest="command")

    # all — 全量基金列表
    p_all = sub.add_parser("all", help="采集全量基金列表")
    p_all.add_argument("--limit", type=int, default=0, help="最多采集 N 只基金详情（0=全部）")
    p_all.add_argument("--skip-detail", action="store_true", help="跳过批量详情")

    # details — 从 MySQL 采集已有基金的详情
    p_det = sub.add_parser("details", help="从 MySQL 采集基金详情")
    p_det.add_argument("--limit", type=int, default=200, help="最多采集 N 只（默认200, 0=全部）")
    p_det.add_argument("--threads", type=int, default=8, help="并发线程数")

    # detail — 单只基金详情
    p_dtl = sub.add_parser("detail", help="采集基金详情")
    p_dtl.add_argument("code", help="基金代码")

    # nav — 净值历史
    p_nav = sub.add_parser("nav", help="采集基金净值")
    p_nav.add_argument("code", help="基金代码")
    p_nav.add_argument("--days", type=int, default=365)

    # holdings — 持仓
    p_hold = sub.add_parser("holdings", help="采集基金持仓")
    p_hold.add_argument("code", help="基金代码")

    args = parser.parse_args()
    crawler = FundCrawler()

    if args.command == "all":
        df = crawler.fetch_all_funds()
        if not df.empty and not args.skip_detail:
            codes = df["fund_code"].head(args.limit).tolist() if args.limit else df["fund_code"].tolist()
            print(f"\n📋 开始批量采集 {len(codes)} 只基金详情...")
            crawler.batch_fetch_details(codes)
    elif args.command == "details":
        # 从 MySQL 读取已有基金代码
        try:
            import pymysql
            conn = crawler._get_mysql_conn()
            cur = conn.cursor()
            cur.execute("SELECT fund_code FROM fund ORDER BY scale DESC, fund_code")
            all_codes = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ 连接 MySQL 失败: {e}，回退到 fund_basic CSV")
            import glob
            files = sorted(Path(str(DATA_DIR)).glob("fund_basic_*.csv"))
            if not files:
                print("⚠️  也未找到 fund_basic CSV 文件")
                return
            df = pd.read_csv(files[-1])
            all_codes = df["fund_code"].tolist()

        codes = all_codes[:args.limit] if args.limit else all_codes
        print(f"📋 从 MySQL 读取 {len(all_codes)} 只基金，本次采集 {len(codes)} 只")
        crawler.batch_fetch_details(codes, threads=args.threads)
    elif args.command == "detail":
        crawler.fetch_fund_detail(args.code)
    elif args.command == "nav":
        crawler.fetch_nav(args.code, args.days)
    elif args.command == "holdings":
        crawler.fetch_holdings(args.code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
