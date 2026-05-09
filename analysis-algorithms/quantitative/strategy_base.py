"""
量化策略基类 — 策略模式

所有策略继承 BaseStrategy，实现:
  - generate_signals(): 根据数据生成买卖信号
  - get_name(): 策略名称
"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self):
        self._signals: pd.DataFrame = None

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成买卖信号
        Args:
            df: K线数据 (date, open, high, low, close, volume)
        Returns:
            添加 signal 列的 DataFrame:
              signal = 1 (买入), -1 (卖出), 0 (持有)
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """策略名称"""
        ...

    def get_params(self) -> dict:
        """策略参数"""
        return {}

    def get_signals(self) -> pd.DataFrame:
        return self._signals
