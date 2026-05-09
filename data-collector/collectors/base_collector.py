"""
数据采集器抽象基类
定义统一的数据采集接口，所有数据源采集器必须继承此类
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd


class BaseCollector(ABC):
    """数据采集器基类 — 策略模式中的 Strategy 接口"""

    # 数据源唯一标识
    source_name: str = "base"

    # 支持的数据类型
    SUPPORTED_MARKETS = ["a_stock", "hk_stock", "us_stock", "fund", "index"]

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._last_result: Optional[pd.DataFrame] = None

    # -----------------------------------------------------------
    # 抽象方法 — 子类必须实现
    # -----------------------------------------------------------

    @abstractmethod
    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情
        Args:
            codes: 股票代码列表，如 ["000001", "600519"]
        Returns:
            DataFrame with columns: code, name, price, change, change_pct, volume, amount, timestamp
        """
        ...

    @abstractmethod
    def fetch_history_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = "daily",
    ) -> pd.DataFrame:
        """获取历史K线数据
        Args:
            code: 股票代码
            start_date: 起始日期 YYYYMMDD，默认2年前
            end_date: 结束日期 YYYYMMDD，默认今天
            freq: K线频率 daily/weekly/monthly
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        ...

    @abstractmethod
    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """获取股票基本信息
        Args:
            codes: 股票代码列表，为 None 则获取全量
        Returns:
            DataFrame with columns: code, name, market, industry, listing_date
        """
        ...

    # -----------------------------------------------------------
    # 可选方法 — 部分数据源可实现
    # -----------------------------------------------------------

    def fetch_fund_nav(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取基金净值数据（可选实现）"""
        raise NotImplementedError(f"{self.source_name} 不支持基金净值查询")

    # -----------------------------------------------------------
    # 通用工具方法
    # -----------------------------------------------------------

    def _default_date_range(self, years: int = 2) -> tuple:
        """生成默认的日期范围 (start_date, end_date)"""
        end = datetime.now()
        start = end - timedelta(days=int(years * 365))
        return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    def save_to_csv(self, df: pd.DataFrame, filepath: str) -> str:
        """保存 DataFrame 到 CSV 文件"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        self._last_result = df
        return str(path)

    def get_last_result(self) -> Optional[pd.DataFrame]:
        """获取最近一次采集结果"""
        return self._last_result

    def health_check(self) -> bool:
        """健康检查 — 检测数据源是否可达"""
        try:
            df = self.fetch_realtime_quotes(["000001"])
            return not df.empty
        except Exception:
            return False
