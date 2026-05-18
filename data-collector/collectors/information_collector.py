"""
资讯层采集器 — 统一研报层 + 新闻层 + 公告层

从 a-stock-data 项目迁移合并，覆盖：
  研报层: 东财研报列表 + PDF下载 + 机构一致预期EPS + iwencai语义搜索
  新闻层: 个股新闻(东财) + 财联社快讯 + 全球资讯
  公告层: 巨潮公告

数据源: akshare / 东财 reportapi / iwencai OpenAPI / 巨潮 cninfo
字段完整性与业务逻辑保持与 a-stock-data 一致
"""

import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


# ============================================================
# iwencai 语义搜索配置（需免费申请 API Key）
# ============================================================
IWENCAI_DEFAULT_KEY = ""
IWENCAI_BASE_URL = "https://gw.iwencai.com/gateway/darwin/api/v1/search"

# ============================================================
# 东财报报告 API 配置
# ============================================================
EASTMONEY_REPORT_URL = "https://reportapi.eastmoney.com/report/list"
EASTMONEY_REPORT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Referer": "https://data.eastmoney.com/report/",
}


class InformationCollector(BaseCollector):
    """资讯层采集器 — 研报 + 新闻 + 公告 统一入口

    继承 BaseCollector，享受基类的熔断器、指数退避重试、数据校验等能力。
    内部整合三种数据来源:
      - akshare 封装 (个股新闻/财联社/全球资讯/巨潮公告)
      - 东财 reportapi (研报列表/PDF)
      - iwencai OpenAPI (自然语言语义搜索)
    """

    source_name = "information"
    SUPPORTED_MARKETS = ["a_stock"]

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._ak = None
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        })
        # iwencai 配置
        self.iwencai_key = (config or {}).get("iwencai_key", IWENCAI_DEFAULT_KEY)

    @property
    def ak(self):
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak

    # ==========================================================
    # 研报层 — Research Reports
    # ==========================================================

    def fetch_research_reports(self, code: str, max_pages: int = 5) -> list:
        """拉取指定股票的研报列表（东财 reportapi）

        返回示例:
          [{
            "stockCode": "688017",
            "title": "公司发布2026年Q1财报，净利润同比增长35%",
            "publishDate": "2026-05-12",
            "orgSName": "中信证券",
            "rating": "买入",
            "predictEpsThisYear": 2.35,
            "predictEpsNextYear": 3.12,
            "infoCode": "H3_688017_1",
            "pageUrl": "..."
          }, ...]

        Args:
            code: 股票代码
            max_pages: 最大翻页数，默认5页(每页100条)
        Returns:
            研报记录列表
        """
        all_records = []
        for page in range(1, max_pages + 1):
            params = {
                "industryCode": "*", "pageSize": "100", "industry": "*",
                "rating": "*", "ratingChange": "*",
                "beginTime": "2000-01-01", "endTime": "2030-01-01",
                "pageNo": str(page), "fields": "", "qType": "0",
                "orgCode": "", "code": code, "rcode": "",
                "p": str(page), "pageNum": str(page), "pageNumber": str(page),
            }
            try:
                r = self._session.get(
                    EASTMONEY_REPORT_URL, params=params,
                    headers=EASTMONEY_REPORT_HEADERS, timeout=30,
                )
                d = r.json()
                rows = d.get("data") or []
                if not rows:
                    break
                for row in rows:
                    all_records.append({
                        "stock_code": code,
                        "title": row.get("title", ""),
                        "publish_date": (row.get("publishDate") or "")[:10],
                        "org_name": row.get("orgSName", ""),
                        "rating": row.get("rating", "") or row.get("emRating", ""),
                        "predict_eps_this_year": row.get("predictEpsThisYear"),
                        "predict_eps_next_year": row.get("predictEpsNextYear"),
                        "info_code": row.get("infoCode", ""),
                        "page_url": row.get("pageUrl", ""),
                        "source": self.source_name,
                    })
                if page >= (d.get("TotalPage", 1) or 1):
                    break
                time.sleep(0.3)
            except Exception as e:
                logger.warning("[%s] 研报列表第%d页采集失败: %s", self.source_name, page, e)
                break
        return all_records

    def download_report_pdf(self, record: dict, target_dir: str = "./reports") -> str:
        """下载研报PDF（东财PDF）

        Args:
            record: fetch_research_reports 返回的单条记录
            target_dir: PDF 保存目录
        Returns:
            PDF 文件路径，失败返回 None
        """
        info_code = record.get("info_code", "")
        if not info_code:
            return None
        date = (record.get("publish_date") or "")[:10]
        org = record.get("org_name") or "未知"
        title = re.sub(r'[\\/:*?"<>|]', "_", record.get("title", ""))[:80]
        fname = f"{date}_{org}_{title}.pdf"
        target = Path(target_dir) / fname
        if target.exists():
            return str(target)
        url = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"
        try:
            r = requests.get(
                url,
                headers={
                    "User-Agent": self._session.headers["User-Agent"],
                    "Referer": "https://data.eastmoney.com/",
                },
                timeout=60,
            )
            if r.status_code == 200 and len(r.content) >= 1024:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(r.content)
                return str(target)
        except Exception as e:
            logger.warning("[%s] 研报PDF下载失败 [%s]: %s", self.source_name, info_code, e)
        return None

    def fetch_consensus_eps(self, code: str) -> pd.DataFrame:
        """机构一致预期EPS（同花顺源）

        返回: DataFrame(columns: 年度, 预测机构数, 最小值, 均值, 最大值, 行业平均数)
        """
        try:
            df = self.ak.stock_profit_forecast_ths(symbol=code, indicator="预测年报每股收益")
            if df.empty:
                return df
            df["code"] = code
            df["source"] = self.source_name
            return df
        except Exception as e:
            raise RuntimeError(f"[{self.source_name}] 一致预期EPS采集失败 [{code}]: {e}")

    def iwencai_search(self, query: str, api_key: str = None) -> list:
        """iwencai 自然语言跨主题研报检索（需 API Key）

        Args:
            query: 自然语言查询，如 "人形机器人 行星滚柱丝杠 2026"
            api_key: iwencai OpenAPI Key，默认使用配置中的 key
        Returns:
            [{title, content, publish_date, source, url, ...}]
        """
        key = api_key or self.iwencai_key
        if not key:
            logger.warning("[%s] iwencai API Key 未配置，跳过语义搜索", self.source_name)
            return []

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "X-Claw-Client": "claude-code",
                "X-Claw-Key": key,
                "Content-Type": "application/json",
            }
            payload = {
                "query": query,
                "source": "report",
                "page": 1,
                "size": 20,
            }
            r = self._session.post(
                IWENCAI_BASE_URL, json=payload, headers=headers, timeout=30,
            )
            if r.status_code == 401:
                logger.warning("[%s] iwencai 401: API Key 无效或未配置", self.source_name)
                return []
            data = r.json()
            results = []
            for item in data.get("data", []):
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "publish_date": (item.get("publishDate") or "")[:10],
                    "source": "iwencai",
                    "url": item.get("url", ""),
                    "query": query,
                })
            return results
        except Exception as e:
            logger.warning("[%s] iwencai 搜索失败: %s", self.source_name, e)
            return []

    # ==========================================================
    # 新闻层 — News
    # ==========================================================

    def fetch_stock_news(self, code: str) -> pd.DataFrame:
        """个股新闻（东财源）

        返回: DataFrame(columns 取决于 akshare)
        """
        try:
            df = self.ak.stock_news_em(symbol=code)
            if not df.empty:
                df["code"] = code
                df["source"] = self.source_name
            return df
        except Exception as e:
            raise RuntimeError(f"[{self.source_name}] 个股新闻采集失败 [{code}]: {e}")

    def fetch_cls_news(self) -> pd.DataFrame:
        """财联社快讯（分钟级电报）

        返回: DataFrame(columns 取决于 akshare)
        """
        try:
            return self.ak.stock_info_global_cls()
        except Exception as e:
            raise RuntimeError(f"[{self.source_name}] 财联社快讯采集失败: {e}")

    def fetch_global_news(self) -> pd.DataFrame:
        """东财全球财经资讯

        返回: DataFrame(columns 取决于 akshare)
        """
        try:
            return self.ak.stock_info_global_em()
        except Exception as e:
            raise RuntimeError(f"[{self.source_name}] 全球资讯采集失败: {e}")

    # ==========================================================
    # 公告层 — Filings
    # ==========================================================

    def fetch_cninfo_filings(self, code: str) -> pd.DataFrame:
        """巨潮公告全文

        根据股票代码前缀自动判断市场：
          6 → 沪市, 8/4 → 北交所, 其余 → 深市

        返回: DataFrame(columns 取决于 akshare)
        """
        try:
            if code.startswith("6"):
                market = "沪市"
            elif code.startswith(("8", "4")):
                market = "北交所"
            else:
                market = "深市"
            df = self.ak.stock_zh_a_disclosure_report_cninfo(symbol=code, market=market)
            if not df.empty:
                df["code"] = code
                df["market"] = market
                df["source"] = self.source_name
            return df
        except Exception as e:
            raise RuntimeError(f"[{self.source_name}] 巨潮公告采集失败 [{code}]: {e}")

    # ==========================================================
    # 基类接口实现
    # ==========================================================

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """资讯层不提供实时行情"""
        raise NotImplementedError("资讯层不提供实时行情，请使用 tencent/mootdx")

    def health_check(self) -> bool:
        """健康检查 — 测试一致预期EPS端点"""
        try:
            df = self.fetch_consensus_eps("000001")
            return not df.empty
        except Exception:
            return False
