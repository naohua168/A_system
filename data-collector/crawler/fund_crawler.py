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

        # 使用东方财富基金详情 API
        url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
        try:
            r = self._session.get(url, timeout=15)
            text = r.text
        except Exception as e:
            logger.error("基金详情请求失败 [%s]: %s", code, e)
            return {}

        result = {"fund_code": code}

        # 从 JavaScript 变量中解析关键字段
        try:
            # 提取 Data_netWorthTrend (净值趋势 - 用于验证)
            import re
            # 基金公司
            m = re.search(r'Data_ManagerCompany\s*=\s*["\']([^"\']+)', text)
            if m:
                result["company"] = m.group(1)
            # 基金经理
            m = re.search(r'Data_Manager\s*=\s*["\']([^"\']+)', text)
            if m:
                result["manager"] = m.group(1)
            # 基金规模
            m = re.search(r'Data_FundScale\s*=\s*([\d.]+)', text)
            if m:
                result["scale"] = float(m.group(1))
            # 基金类型
            m = re.search(r'Data_FundType\s*=\s*["\']([^"\']+)', text)
            if m:
                result["fund_type"] = m.group(1)
        except Exception as e:
            logger.warning("基金详情解析失败 [%s]: %s", code, e)

        print(f"  基金: {result.get('fund_name', code)} | "
              f"公司: {result.get('company', '--')} | "
              f"经理: {result.get('manager', '--')} | "
              f"规模: {result.get('scale', '--')}亿")

        if save and result.get("company") or result.get("manager"):
            fp = str(DATA_DIR / f"fund_detail_{code}_{datetime.now():%Y%m%d}.csv")
            pd.DataFrame([result]).to_csv(fp, index=False, encoding="utf-8-sig")
            print(f"💾 已保存: {fp}")
        return result

    # ──────────────────────────────────────────────
    # 3. 批量采集基金详情
    # ──────────────────────────────────────────────
    def batch_fetch_details(self, codes: list, save: bool = True):
        """批量采集基金详情"""
        total = len(codes)
        results = []
        for i, code in enumerate(codes):
            print(f"[{i + 1}/{total}] ", end="")
            detail = self.fetch_fund_detail(code, save=False)
            if detail:
                results.append(detail)
            time.sleep(0.5)  # 防反爬
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


def main():
    parser = argparse.ArgumentParser(description="📊 基金数据采集器 v2")
    sub = parser.add_subparsers(dest="command")

    # all — 全量基金列表
    p_all = sub.add_parser("all", help="采集全量基金列表 + 批量详情")
    p_all.add_argument("--skip-detail", action="store_true", help="跳过批量详情")

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
            codes = df["fund_code"].head(50).tolist()  # 先采前50只
            print(f"\n📋 开始批量采集 {len(codes)} 只基金详情...")
            crawler.batch_fetch_details(codes)
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
