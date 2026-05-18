"""
量化策略基类 — 策略模式

所有策略继承 BaseStrategy，实现:
  - generate_signals(): 根据数据生成买卖信号
  - get_name(): 策略名称

框架核心类:
  - BaseStrategy: 策略基类（抽象）
  - StrategyEngine: 策略引擎（组合多个策略，统一运行）
"""

from abc import ABC, abstractmethod
from typing import List

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


class StrategyEngine:
    """策略引擎 — 组合多个策略，统一运行并汇总信号

    用法:
        engine = StrategyEngine()
        engine.add_strategy(MAStrategy())
        engine.add_strategy(MomentumStrategy())
        signals = engine.run_all(kline_df)
    """

    def __init__(self):
        self._strategies: List[BaseStrategy] = []

    def add_strategy(self, strategy: BaseStrategy):
        """注册策略"""
        if not isinstance(strategy, BaseStrategy):
            raise TypeError(f"策略必须继承 BaseStrategy，收到 {type(strategy)}")
        self._strategies.append(strategy)

    def run_all(self, df: pd.DataFrame) -> List[dict]:
        """运行所有已注册的策略，返回聚合信号列表

        Args:
            df: K线数据 (open, high, low, close, volume)
        Returns:
            [{date, strategy, signal, ...}, ...]
        """
        all_signals = []
        for strategy in self._strategies:
            try:
                result = strategy.generate_signals(df)
                name = strategy.get_name()
                for _, row in result.iterrows():
                    sig_val = row.get("signal", 0)
                    if sig_val != 0:
                        all_signals.append({
                            "date": row.get("date", ""),
                            "strategy": name,
                            "signal": int(sig_val),
                            "type": "buy" if sig_val > 0 else "sell",
                        })
            except Exception as e:
                raise RuntimeError(f"策略 [{strategy.get_name()}] 运行失败: {e}")

        return all_signals

    def get_strategy_count(self) -> int:
        return len(self._strategies)
