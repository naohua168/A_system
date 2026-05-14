"""
同花顺热点采集器
覆盖：
1. 当日强势股 + 题材归因 reason tags（编辑部人工运营，零鉴权73ms）
2. 北向资金实时分钟流向（hsgtApi）+ 本地自缓存历史

数据特点：HTTP直连，零鉴权，无需cookie/API Key
"""
from datetime import date as _date
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from .base_collector import BaseCollector


class ThsHotCollector(BaseCollector):
    """同花顺热点 — 当日强势股 + 题材归因"""

    source_name = "ths_hot"
    SUPPORTED_MARKETS = ["a_stock"]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
    }

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        raise NotImplementedError("同花顺热点是强势股归因，不是实时行情接口")

    def fetch_hot_reason(self, date_str: str = None) -> pd.DataFrame:
        """当日强势股题材归因

        date_str: 'YYYY-MM-DD', None=今天
        返回: 代码, 名称, 涨幅%, 题材归因(核心字段), 换手率%, 成交额, 大单净量
        """
        if date_str is None:
            date_str = _date.today().strftime("%Y-%m-%d")

        url = (
            f"http://zx.10jqka.com.cn/event/api/getharden/"
            f"date/{date_str}/orderby/date/orderway/desc/charset/GBK/"
        )
        r = requests.get(url, headers=self.HEADERS, timeout=10)
        data = r.json()
        if data.get("errocode", 0) != 0:
            raise RuntimeError(f"同花顺热点错误: {data.get('errormsg', '')}")

        rows = data.get("data") or []
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        rename_map = {
            "name": "名称", "code": "代码", "reason": "题材归因",
            "close": "收盘价", "zhangdie": "涨跌额", "zhangfu": "涨幅%",
            "huanshou": "换手率%", "chengjiaoe": "成交额",
            "chengjiaoliang": "成交量", "ddejingliang": "大单净量",
            "market": "市场",
        }
        df = df.rename(columns=rename_map)
        df["source"] = self.source_name
        df["fetch_date"] = date_str
        return df

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        raise NotImplementedError("同花顺热点不提供股票基本信息")

    def health_check(self) -> bool:
        try:
            df = self.fetch_hot_reason()
            return not df.empty
        except Exception:
            return False


class ThsNorthboundCollector(BaseCollector):
    """同花顺北向资金 — hsgtApi实时分钟 + 本地自缓存历史

    V2.1: eastmoney 北向数据断供，改为本地CSV自缓存模式
    """

    source_name = "ths_northbound"
    SUPPORTED_MARKETS = ["a_stock"]

    HSGT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "Chrome/117.0.0.0 Safari/537.36"
        ),
        "Host": "data.hexin.cn",
        "Referer": "https://data.hexin.cn/",
    }

    @staticmethod
    def _cache_path() -> Path:
        p = Path.home() / ".tradingagents" / "cache" / "northbound_daily.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        return self.fetch_hsgt_realtime()

    def fetch_hsgt_realtime(self) -> pd.DataFrame:
        """沪深股通实时分钟流向 (262个时间点 09:10-15:00)"""
        url = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
        r = requests.get(url, headers=self.HSGT_HEADERS, timeout=10)
        d = r.json()
        times = d.get("time", [])
        hgt = d.get("hgt", [])
        sgt = d.get("sgt", [])
        n = len(times)
        df = pd.DataFrame({
            "time": times,
            "hgt_yi": hgt[:n] + [None] * (n - len(hgt)),
            "sgt_yi": sgt[:n] + [None] * (n - len(sgt)),
        })
        df["source"] = self.source_name
        return df

    def save_daily_snapshot(self, date_str: str, hgt: float, sgt: float):
        """写入当天北向收盘数据到本地缓存"""
        path = self._cache_path()
        rows = {}
        if path.exists():
            for line in path.read_text().strip().split("\n")[1:]:
                parts = line.split(",")
                if len(parts) == 3:
                    rows[parts[0]] = line
        rows[date_str] = f"{date_str},{hgt},{sgt}"
        with open(path, "w") as f:
            f.write("date,hgt,sgt\n")
            for d in sorted(rows.keys()):
                f.write(rows[d] + "\n")

    def load_history(self, n: int = 20) -> pd.DataFrame:
        """读取最近N天北向历史"""
        path = self._cache_path()
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path).tail(n)

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        raise NotImplementedError("北向资金不提供股票基本信息")

    def health_check(self) -> bool:
        try:
            df = self.fetch_hsgt_realtime()
            return not df.empty
        except Exception:
            return False
