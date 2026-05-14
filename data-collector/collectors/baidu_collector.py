"""
百度股市通采集器（PAE协议）
覆盖：概念板块归属（行业/概念/地域三维）+ 个股资金流向（分钟级+20日历史）
数据特点：HTTP直连，零鉴权，需处理 ResultCode 类型不稳定（int/string）
"""
from typing import List, Optional

import pandas as pd
import requests

from .base_collector import BaseCollector

_BAIDU_HEADERS = {
    "Host": "finance.pae.baidu.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0",
    "Accept": "application/vnd.finance-web.v1+json",
    "Origin": "https://gushitong.baidu.com",
    "Referer": "https://gushitong.baidu.com/",
}


class BaiduCollector(BaseCollector):
    """百度股市通 — 概念板块 + 资金流向"""

    source_name = "baidu"
    SUPPORTED_MARKETS = ["a_stock"]

    # ==========================================================
    # 概念板块归属
    # ==========================================================

    def fetch_concept_blocks(self, code: str) -> dict:
        """概念板块归属（行业/概念/地域三维）

        返回: {industry: [{name, change_pct, desc}],
               concept: [{name, change_pct, desc}],
               region: [{name, change_pct, desc}],
               concept_tags: [str]}
        """
        url = (
            f"https://finance.pae.baidu.com/api/getrelatedblock"
            f"?code={code}&market=ab&typeCode=all&finClientType=pc"
        )
        r = requests.get(url, headers=_BAIDU_HEADERS, timeout=10)
        d = r.json()
        # ResultCode 可能 int 也可能 string
        if str(d.get("ResultCode", -1)) != "0":
            raise RuntimeError(f"百度PAE错误: {d}")

        result = {"industry": [], "concept": [], "region": [], "concept_tags": []}
        for block in d.get("Result", []):
            block_type = block.get("type", "")
            for item in block.get("list", []):
                entry = {
                    "name": item.get("name", ""),
                    "change_pct": item.get("increase", ""),
                    "desc": item.get("desc", ""),
                }
                if "行业" in block_type:
                    result["industry"].append(entry)
                elif "概念" in block_type:
                    result["concept"].append(entry)
                    result["concept_tags"].append(entry["name"])
                elif "地域" in block_type:
                    result["region"].append(entry)
        return result

    # ==========================================================
    # 个股资金流向（分钟级）
    # ==========================================================

    def fetch_fund_flow_realtime(self, code: str, date: str = None) -> list:
        """个股资金流向（分钟级）

        date: YYYYMMDD 紧凑格式
        返回: [{time, mainForce, retail, super, large, price}, ...]
        """
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y%m%d")

        url = (
            f"https://finance.pae.baidu.com/vapi/v1/fundflow"
            f"?code={code}&market=ab&date={date}&finClientType=pc"
        )
        r = requests.get(url, headers=_BAIDU_HEADERS, timeout=10)
        d = r.json()
        if str(d.get("ResultCode", -1)) != "0":
            return []

        raw = d.get("Result", {}).get("update_data", "")
        if not raw:
            return []

        rows = []
        for segment in raw.split(";"):
            parts = segment.split(",")
            if len(parts) >= 9:
                rows.append({
                    "time": parts[0],
                    "mainForce": float(parts[2]) if parts[2] else 0,
                    "retail": float(parts[3]) if parts[3] else 0,
                    "super": float(parts[4]) if parts[4] else 0,
                    "large": float(parts[5]) if parts[5] else 0,
                    "price": float(parts[8]) if parts[8] else 0,
                })
        return rows

    # ==========================================================
    # 个股资金流向（20日历史）
    # ==========================================================

    def fetch_fund_flow_history(self, code: str, days: int = 20) -> list:
        """个股资金流向（日级历史）

        返回: [{date, close, change_pct, superNetIn, largeNetIn,
                mediumNetIn, littleNetIn, mainIn}, ...]
        """
        url = (
            f"https://finance.pae.baidu.com/vapi/v1/fundsortlist"
            f"?code={code}&market=ab&pn=0&rn={days}&finClientType=pc"
        )
        r = requests.get(url, headers=_BAIDU_HEADERS, timeout=10)
        d = r.json()
        if str(d.get("ResultCode", -1)) != "0":
            return []

        rows = []
        for item in d.get("Result", {}).get("list", []):
            rows.append({
                "date": item.get("showtime", ""),
                "close": item.get("closepx", ""),
                "change_pct": item.get("ratio", ""),
                "superNetIn": item.get("superNetIn", ""),
                "largeNetIn": item.get("largeNetIn", ""),
                "mediumNetIn": item.get("mediumNetIn", ""),
                "littleNetIn": item.get("littleNetIn", ""),
                "mainIn": item.get("extMainIn", ""),
            })
        return rows

    # ==========================================================
    # 接口实现（兼容基类）
    # ==========================================================

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        raise NotImplementedError("百度不提供批量实时行情，请用 tencent/mootdx")

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        raise NotImplementedError("百度不提供股票基本信息")

    def health_check(self) -> bool:
        try:
            result = self.fetch_concept_blocks("000001")
            return bool(result.get("concept_tags"))
        except Exception:
            return False
