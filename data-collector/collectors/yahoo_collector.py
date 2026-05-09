"""
Yahoo Finance 数据采集器
基于 yfinance 开源库，覆盖港股、美股、全球指数
"""

from typing import List, Optional

import pandas as pd

from .base_collector import BaseCollector


class YahooCollector(BaseCollector):
    """Yahoo Finance 数据源 — 通过 yfinance"""

    source_name = "yahoo"

    # Yahoo 支持的金融市场
    SUPPORTED_MARKETS = ["hk_stock", "us_stock", "index"]

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._yf = None

    @property
    def yf(self):
        if self._yf is None:
            import yfinance as yf

            self._yf = yf
        return self._yf

    # ==========================================================
    # 实时行情
    # ==========================================================

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """Yahoo 实时行情 — 通过 yfinance.Ticker"""
        records = []
        for code in codes:
            try:
                yahoo_code = self._normalize_code(code)
                ticker = self.yf.Ticker(yahoo_code)
                info = ticker.info
                records.append(
                    {
                        "code": code,
                        "name": info.get("shortName", info.get("longName", "")),
                        "price": info.get("regularMarketPrice"),
                        "change": info.get("regularMarketChange"),
                        "change_pct": info.get("regularMarketChangePercent"),
                        "volume": info.get("regularMarketVolume"),
                        "open": info.get("regularMarketOpen"),
                        "high": info.get("regularMarketDayHigh"),
                        "low": info.get("regularMarketDayLow"),
                        "pre_close": info.get("regularMarketPreviousClose"),
                        "market": info.get("market", ""),
                        "source": self.source_name,
                        "timestamp": pd.Timestamp.now(),
                    }
                )
            except Exception as e:
                print(f"Yahoo 获取 {code} 失败: {e}")
                continue
        return pd.DataFrame(records)

    # ==========================================================
    # 历史K线
    # ==========================================================

    def fetch_history_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = "daily",
    ) -> pd.DataFrame:
        """Yahoo 历史K线 — 适合港股/美股"""
        if not start_date or not end_date:
            start_date, end_date = self._default_date_range()

        yahoo_code = self._normalize_code(code)
        interval_map = {
            "daily": "1d",
            "weekly": "1wk",
            "monthly": "1mo",
            "60min": "60m",
        }
        interval = interval_map.get(freq, "1d")

        try:
            ticker = self.yf.Ticker(yahoo_code)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
            )
            if df.empty:
                return df

            df = df.reset_index()
            result = df.rename(
                columns={
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                    "Dividends": "dividends",
                    "Stock Splits": "stock_splits",
                }
            )
            # 统一日期格式
            result["date"] = result["date"].dt.strftime("%Y-%m-%d")
            result["code"] = code
            result["source"] = self.source_name
            return result
        except Exception as e:
            raise RuntimeError(f"Yahoo 历史K线采集失败 [{code}]: {e}")

    # ==========================================================
    # 股票基本信息
    # ==========================================================

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """Yahoo 股票基本信息"""
        if not codes:
            return pd.DataFrame()
        records = []
        for code in codes:
            try:
                yahoo_code = self._normalize_code(code)
                ticker = self.yf.Ticker(yahoo_code)
                info = ticker.info
                records.append(
                    {
                        "code": code,
                        "name": info.get("shortName", info.get("longName", "")),
                        "market": info.get("market", ""),
                        "industry": info.get("industry", ""),
                        "sector": info.get("sector", ""),
                        "market_cap": info.get("marketCap"),
                        "currency": info.get("currency", ""),
                        "listing_date": "-",
                        "source": self.source_name,
                    }
                )
            except Exception as e:
                print(f"Yahoo 获取基本信息失败 [{code}]: {e}")
                continue
        return pd.DataFrame(records)

    # ==========================================================
    # 内部工具
    # ==========================================================

    @staticmethod
    def _normalize_code(code: str) -> str:
        """转为 Yahoo Finance 代码格式
        - A股: 000001.SZ / 600519.SS
        - 港股: 0700.HK
        - 美股: AAPL
        """
        code = code.strip().upper()
        # 如果已包含后缀则直接返回
        if any(suffix in code for suffix in [".SS", ".SZ", ".HK"]):
            return code
        # 港股: hk00700 → 0700.HK
        if code.startswith("HK"):
            return code[2:] + ".HK"
        # A股: 6 → .SS, 0/3 → .SZ
        if code.startswith("6"):
            return code + ".SS"
        if code.startswith(("0", "3")):
            return code + ".SZ"
        # 美股直接返回
        return code
