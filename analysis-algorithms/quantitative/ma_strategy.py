"""
均线策略 — 金叉买入 / 死叉卖出

信号规则:
  - 短线上穿长线 (金叉) → 买入
  - 短线下穿长线 (死叉) → 卖出
  - 其他情况 → 持有
"""

import pandas as pd

from .strategy_base import BaseStrategy


class MAStrategy(BaseStrategy):
    """均线交叉策略"""

    def __init__(self, fast: int = 5, slow: int = 20):
        super().__init__()
        self.fast = fast
        self.slow = slow

    def get_name(self) -> str:
        return f"MA{self.fast}_{self.slow}_Cross"

    def get_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        # 计算均线
        result[f"MA{self.fast}"] = result["close"].rolling(self.fast).mean()
        result[f"MA{self.slow}"] = result["close"].rolling(self.slow).mean()

        # 信号: 1=买入, -1=卖出, 0=持有
        result["signal"] = 0

        # 金叉: 短线上穿长线
        result.loc[result[f"MA{self.fast}"] > result[f"MA{self.slow}"], "temp"] = 1
        result.loc[result[f"MA{self.fast}"] <= result[f"MA{self.slow}"], "temp"] = -1
        result["cross"] = result["temp"].diff()
        result.loc[result["cross"] == 2, "signal"] = 1   # 金叉买入
        result.loc[result["cross"] == -2, "signal"] = -1 # 死叉卖出

        result = result.drop(columns=["temp", "cross"], errors="ignore")
        self._signals = result
        return result
