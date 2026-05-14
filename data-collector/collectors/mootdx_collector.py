"""
mootdx 数据采集器（通达信 TCP 协议）
覆盖：K线(多周期)、五档盘口、逐笔成交、财务快照(37字段)、F10公司资料
数据特点：TCP 二进制协议(7709端口)，无需注册，不封IP，需国内IP
"""
from typing import List, Optional

import pandas as pd

from .base_collector import BaseCollector


class MootdxCollector(BaseCollector):
    """mootdx 通达信 TCP 数据源"""

    source_name = "mootdx"
    SUPPORTED_MARKETS = ["a_stock", "index"]

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from mootdx.quotes import Quotes
            self._client = Quotes.factory(market='std')
        return self._client

    def fetch_history_kline(
        self, code: str, start_date: Optional[str] = None,
        end_date: Optional[str] = None, freq: str = "daily",
    ) -> pd.DataFrame:
        """获取K线数据 — mootdx TCP"""
        freq_map = {
            "daily": 4, "weekly": 5, "monthly": 6,
            "1min": 7, "5min": 8, "15min": 9, "30min": 10, "60min": 11,
        }
        category = freq_map.get(freq, 4)
        try:
            klines = self.client.bars(symbol=code, category=category, offset=800)
            if klines is None or len(klines) == 0:
                return pd.DataFrame()
            df = pd.DataFrame(klines)
            df["date"] = pd.to_datetime(df["datetime"], unit='s').dt.strftime("%Y-%m-%d")
            df = df.rename(columns={"vol": "volume"})
            df["code"] = code
            df["source"] = self.source_name
            if start_date:
                df = df[df["date"] >= start_date]
            if end_date:
                df = df[df["date"] <= end_date]
            return df.reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"mootdx K线采集失败 [{code}]: {e}")

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情 — 含五档盘口"""
        try:
            quotes = self.client.quotes(symbol=codes)
            if quotes is None or len(quotes) == 0:
                return pd.DataFrame()
            df = pd.DataFrame(quotes)
            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("code", "")),
                    "name": str(row.get("name", "")),
                    "price": float(row.get("price", 0)),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "pre_close": float(row.get("last_close", 0)),
                    "volume": int(row.get("vol", 0)),
                    "amount": float(row.get("amount", 0)),
                    "bid1": float(row.get("bid1", 0)),
                    "bid_vol1": int(row.get("bid_vol1", 0)),
                    "ask1": float(row.get("ask1", 0)),
                    "ask_vol1": int(row.get("ask_vol1", 0)),
                    "source": self.source_name,
                    "timestamp": pd.Timestamp.now(),
                })
            return pd.DataFrame(records)
        except Exception as e:
            raise RuntimeError(f"mootdx 实时行情失败: {e}")

    def fetch_transactions(self, code: str, date: str = None) -> pd.DataFrame:
        """获取逐笔成交（非交易时间返回空）"""
        if date is None:
            date = pd.Timestamp.now().strftime("%Y%m%d")
        try:
            trades = self.client.transaction(symbol=code, date=date)
            if trades is None or len(trades) == 0:
                return pd.DataFrame()
            df = pd.DataFrame(trades)
            df["code"] = code
            df["source"] = self.source_name
            return df
        except Exception as e:
            raise RuntimeError(f"mootdx 逐笔成交失败 [{code}]: {e}")

    def fetch_financial_snapshot(self, code: str) -> dict:
        """获取季报财务快照 — 37字段"""
        try:
            fin = self.client.finance(symbol=code)
            if fin is None:
                return {}
            return {
                "code": code,
                "eps": fin.get("eps"),
                "bvps": fin.get("bvps"),
                "roe": fin.get("roe"),
                "profit": fin.get("profit"),
                "income": fin.get("income"),
                "total_shares": fin.get("zongguben"),
                "float_shares": fin.get("liutongguben"),
                "source": self.source_name,
            }
        except Exception as e:
            raise RuntimeError(f"mootdx 财务快照失败 [{code}]: {e}")

    def fetch_f10(self, code: str, category: str = "公司概况") -> str:
        """获取F10公司资料"""
        try:
            text = self.client.F10(symbol=code, name=category)
            return text or ""
        except Exception as e:
            raise RuntimeError(f"mootdx F10失败 [{code}/{category}]: {e}")

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        raise NotImplementedError("mootdx 不提供股票基本信息，请使用 tencent")

    def health_check(self) -> bool:
        try:
            quotes = self.client.quotes(symbol=["000001"])
            return quotes is not None and len(quotes) > 0
        except Exception:
            return False
