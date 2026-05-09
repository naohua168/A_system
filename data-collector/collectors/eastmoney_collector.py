"""
东方财富数据采集器
基于 akshare 开源库封装，覆盖 A 股行情、K线、基金、板块等
"""

from typing import List, Optional

import pandas as pd

from .base_collector import BaseCollector


class EastMoneyCollector(BaseCollector):
    """东方财富数据源 — 通过 akshare 调用"""

    source_name = "eastmoney"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._akshare = None  # lazy import

    @property
    def ak(self):
        if self._akshare is None:
            import akshare as ak

            self._akshare = ak
        return self._akshare

    # ==========================================================
    # 实时行情
    # ==========================================================

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """东方财富实时行情 — 通过 akshare.stock_zh_a_spot_em"""
        codes_str = ",".join(codes)
        try:
            df = self.ak.stock_zh_a_spot_em()
            # 过滤指定代码
            if codes and codes[0] != "*":
                df = df[df["代码"].isin(codes)]
            if df.empty:
                return df

            result = df.rename(
                columns={
                    "代码": "code",
                    "名称": "name",
                    "最新价": "price",
                    "涨跌幅": "change_pct",
                    "涨跌额": "change",
                    "成交量": "volume",
                    "成交额": "amount",
                    "今开": "open",
                    "最高": "high",
                    "最低": "low",
                    "昨收": "pre_close",
                }
            )
            result["source"] = self.source_name
            result["timestamp"] = pd.Timestamp.now()
            # 选取关键列
            cols = [
                "code", "name", "price", "change", "change_pct",
                "volume", "amount", "open", "high", "low", "pre_close",
                "source", "timestamp",
            ]
            return result[[c for c in cols if c in result.columns]]
        except Exception as e:
            raise RuntimeError(f"东方财富实时行情采集失败: {e}")

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
        """东方财富历史K线 — 通过 akshare.stock_zh_a_hist"""
        if not start_date or not end_date:
            start_date, end_date = self._default_date_range()

        # 频率映射
        period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
        period = period_map.get(freq, "daily")

        try:
            # 自动加前缀: sh/sz
            adjusted_code = self._normalize_code(code)
            df = self.ak.stock_zh_a_hist(
                symbol=adjusted_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",  # 前复权
            )
            if df.empty:
                return df

            result = df.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                    "振幅": "amplitude",
                    "涨跌幅": "change_pct",
                    "涨跌额": "change",
                    "换手率": "turnover",
                }
            )
            result["code"] = code
            result["source"] = self.source_name
            return result
        except Exception as e:
            raise RuntimeError(f"东方财富历史K线采集失败 [{code}]: {e}")

    # ==========================================================
    # 股票基本信息
    # ==========================================================

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """东方财富股票基本信息 — 全量A股"""
        try:
            df = self.ak.stock_zh_a_spot_em()
            result = df.rename(
                columns={
                    "代码": "code",
                    "名称": "name",
                    "最新价": "price",
                    "总市值": "total_market_cap",
                    "流通市值": "float_market_cap",
                    "市盈率-动态": "pe",
                    "市净率": "pb",
                    "行业": "industry",
                }
            )
            result["source"] = self.source_name
            if codes and codes[0] != "*":
                result = result[result["code"].isin(codes)]
            return result
        except Exception as e:
            raise RuntimeError(f"东方财富股票基本信息采集失败: {e}")

    # ==========================================================
    # 基金净值
    # ==========================================================

    def fetch_fund_nav(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """东方财富基金净值"""
        if not start_date or not end_date:
            start_date, end_date = self._default_date_range(years=1)
        try:
            df = self.ak.fund_em_open_fund_info(
                symbol=code, indicator="单位净值走势"
            )
            if df.empty:
                return df
            df.columns = ["date", "nav", "accum_nav", "daily_change"]
            df["code"] = code
            df["source"] = self.source_name
            # 按日期筛选
            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
            return df.reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"东方财富基金净值采集失败 [{code}]: {e}")

    # ==========================================================
    # 指数数据
    # ==========================================================

    def fetch_index_realtime(self, codes: List[str] = None) -> pd.DataFrame:
        """获取A股指数实时行情（akshare: stock_zh_index_spot_em）
        如需港股/全球指数，建议通过 YahooCollector 获取。
        """
        try:
            df = self.ak.stock_zh_index_spot_em()
            if codes and codes[0] != "*":
                df = df[df["代码"].isin(codes)]
            if df.empty:
                return df
            result = df.rename(columns={
                "代码": "code", "名称": "name",
                "最新价": "price", "涨跌幅": "change_pct",
                "涨跌额": "change", "成交量": "volume",
                "成交额": "amount", "今开": "open",
                "最高": "high", "最低": "low", "昨收": "pre_close",
            })
            result["source"] = self.source_name
            result["asset_type"] = "index"
            return result
        except Exception as e:
            raise RuntimeError(f"东方财富指数行情采集失败: {e}")

    def fetch_index_kline(self, code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取A股指数日K线（akshare: stock_zh_index_daily_em）"""
        if not start_date or not end_date:
            start_date, end_date = self._default_date_range(years=1)
        try:
            df = self.ak.stock_zh_index_daily_em(symbol=code)
            if df.empty:
                return df
            df.columns = ["date", "open", "close", "high", "low", "volume", "amount", "amplitude", "change_pct", "change", "turnover"]
            df["code"] = code
            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
            return df.reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"东方财富指数K线采集失败 [{code}]: {e}")

    # ==========================================================
    # 内部工具
    # ==========================================================

    @staticmethod
    def _normalize_code(code: str) -> str:
        """将纯数字代码转为 akshare 格式"""
        code = code.strip().upper()
        if code.startswith(("SH", "SZ", "BJ")):
            return code
        # 判断前缀: 6 → sh, 0/3 → sz, 4/8 → bj
        if code.startswith("6"):
            return f"SH{code}"
        elif code.startswith(("0", "3")):
            return f"SZ{code}"
        elif code.startswith(("4", "8")):
            return f"BJ{code}"
        return code
