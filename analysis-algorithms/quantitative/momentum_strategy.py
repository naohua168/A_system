"""
动量策略 — 过去N日收益率排序，买入动量最强的股票

信号规则:
  - 计算过去N日收益率
  - 收益率 > threshold% → 买入
  - 收益率 < -threshold% → 卖出
  - 其他 → 持有
"""
import pandas as pd

from .strategy_base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """动量策略"""

    def __init__(self, lookback: int = 20, threshold: float = 5.0):
        super().__init__()
        self.lookback = lookback
        self.threshold = threshold

    def get_name(self) -> str:
        return f"Momentum_{self.lookback}D_{self.threshold}%"

    def get_params(self) -> dict:
        return {"lookback": self.lookback, "threshold": self.threshold}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        # 计算N日收益率
        result["return"] = result["close"].pct_change(self.lookback) * 100

        # 信号: 1=买入, -1=卖出, 0=持有
        result["signal"] = 0
        result.loc[result["return"] > self.threshold, "signal"] = 1
        result.loc[result["return"] < -self.threshold, "signal"] = -1

        self._signals = result
        return result
