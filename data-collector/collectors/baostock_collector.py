"""
Baostock 数据采集器（免注册、免 token、免费）
覆盖 A 股日/周/月K线、分钟线、基本面数据
"""

import time
from typing import List, Optional

import pandas as pd

from .base_collector import BaseCollector


class BaoStockCollector(BaseCollector):
    """Baostock 数据源 — 免费开源 A 股数据，无需注册"""

    source_name = "baostock"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._bs = None
        self._logged_in = False

    @property
    def bs(self):
        if self._bs is None:
            import baostock as bs

            self._bs = bs
        return self._bs

    def _ensure_login(self):
        """确保已登录 Baostock"""
        if not self._logged_in:
            lg = self.bs.login()
            if lg.error_code != "0":
                raise RuntimeError(f"Baostock 登录失败: {lg.error_msg}")
            self._logged_in = True

    def _logout(self):
        if self._logged_in:
            self.bs.logout()
            self._logged_in = False

    # ==========================================================
    # 实时行情
    # ==========================================================

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """Baostock 不提供实时行情，使用 query_all_stock 获取当日行情"""
        self._ensure_login()
        try:
            today = time.strftime("%Y-%m-%d")
            rs = self.bs.query_all_stock(today)
            if rs.error_code != "0":
                return pd.DataFrame()
            df = rs.get_data()
            if df.empty:
                return pd.DataFrame()
            # 过滤指定代码
            if codes and codes[0] != "*":
                df = df[df["code"].isin(self._add_bs_prefix(codes))]
            if df.empty:
                return df
            result = df.rename(
                columns={
                    "code": "code",
                    "tradeStatus": "trade_status",
                    "code_name": "name",
                }
            )
            result["source"] = self.source_name
            result["timestamp"] = pd.Timestamp.now()
            return result
        finally:
            self._logout()

    # ==========================================================
    # 历史K线（Baostock 强项 — 数据质量高、免费）
    # ==========================================================

    def fetch_history_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = "daily",
    ) -> pd.DataFrame:
        """Baostock 历史K线 — 支持日/周/月/分钟"""
        self._ensure_login()
        try:
            if not start_date or not end_date:
                start_date, end_date = self._default_date_range()

            freq_map = {
                "daily": "d",
                "weekly": "w",
                "monthly": "m",
                "5min": "5",
                "15min": "15",
                "30min": "30",
                "60min": "60",
            }
            adjusted_freq = freq_map.get(freq, "d")
            bs_code = self._normalize_code(code)
            rs = self.bs.query_history_k_data_plus(
                bs_code,
                fields="date,open,high,low,close,volume,amount,turn,tradestatus,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency=adjusted_freq,
                adjustflag="2",  # 前复权
            )
            if rs.error_code != "0":
                raise RuntimeError(f"Baostock K线查询失败: {rs.error_msg}")
            df = rs.get_data()
            if df.empty:
                return df
            # 类型转换
            numeric_cols = ["open", "high", "low", "close", "volume", "amount", "turn", "pctChg"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            result = df.rename(
                columns={
                    "date": "date",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "volume": "volume",
                    "amount": "amount",
                    "turn": "turnover",
                    "pctChg": "change_pct",
                    "tradestatus": "trade_status",
                }
            )
            # 仅保留交易状态为 1 的
            if "trade_status" in result.columns:
                result = result[result["trade_status"] == "1"]
            result["code"] = code
            result["source"] = self.source_name
            return result.reset_index(drop=True)
        finally:
            self._logout()

    # ==========================================================
    # 股票基本信息
    # ==========================================================

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """Baostock 查询 A 股股票基本信息"""
        self._ensure_login()
        try:
            rs = self.bs.query_stock_basic()
            if rs.error_code != "0":
                return pd.DataFrame()
            df = rs.get_data()
            if codes and codes[0] != "*":
                df = df[df["code"].isin(self._add_bs_prefix(codes))]
            result = df.rename(
                columns={
                    "code": "code",
                    "code_name": "name",
                    "status": "trade_status",
                    "ipoDate": "listing_date",
                    "outDate": "delist_date",
                    "type": "stock_type",
                }
            )
            result["source"] = self.source_name
            return result
        finally:
            self._logout()

    # ==========================================================
    # 内部工具
    # ==========================================================

    @staticmethod
    def _normalize_code(code: str) -> str:
        """转为 baostock 格式: sh.600519 / sz.000001"""
        code = code.strip().replace("SH", "").replace("SZ", "").replace("BJ", "")
        if code.startswith("6"):
            return f"sh.{code}"
        elif code.startswith(("0", "3")):
            return f"sz.{code}"
        elif code.startswith(("4", "8")):
            return f"bj.{code}"
        return code

    @staticmethod
    def _add_bs_prefix(codes: List[str]) -> List[str]:
        """给纯数字代码加 baostock 前缀"""
        result = []
        for c in codes:
            c = c.strip().replace("SH", "").replace("SZ", "").replace("BJ", "")
            if c.startswith("6"):
                result.append(f"sh.{c}")
            elif c.startswith(("4", "8")):
                result.append(f"bj.{c}")
            else:
                result.append(f"sz.{c}")
        return result
