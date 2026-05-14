"""
多因子策略 — 综合多个因子评分，生成买卖信号

因子:
  - 动量因子: 过去20日收益率
  - 均值回复因子: 当前价格与MA20的偏离度
  - 成交量因子: 当日成交量与20日均量的比值

信号规则:
  - 综合评分 > 买入阈值 → 买入
  - 综合评分 < 卖出阈值 → 卖出
  - 其他 → 持有
"""
import pandas as pd
import numpy as np

from .strategy_base import BaseStrategy


class MultiFactorStrategy(BaseStrategy):
    """多因子策略"""

    def __init__(self, buy_threshold: float = 1.5, sell_threshold: float = -1.5):
        super().__init__()
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def get_name(self) -> str:
        return f"MultiFactor_{self.buy_threshold}_{self.sell_threshold}"

    def get_params(self) -> dict:
        return {"buy_threshold": self.buy_threshold, "sell_threshold": self.sell_threshold}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        # 因子1: 动量 (过去20日收益率, Z-score标准化)
        momentum = result["close"].pct_change(20)
        result["factor_momentum"] = (
            (momentum - momentum.mean()) / momentum.std()
        ).fillna(0)

        # 因子2: 均值回复 (价格偏离MA20的程度)
        ma20 = result["close"].rolling(20).mean()
        deviation = (result["close"] - ma20) / ma20 * 100
        # 偏离度越大越看空(均值回复), 取负值
        result["factor_reversion"] = -(
            (deviation - deviation.mean()) / deviation.std()
        ).fillna(0)

        # 因子3: 成交量比 (当日量 / 20日均量)
        vol_ma20 = result["volume"].rolling(20).mean()
        vol_ratio = result["volume"] / vol_ma20
        result["factor_volume"] = (
            (vol_ratio - vol_ratio.mean()) / vol_ratio.std()
        ).fillna(0)

        # 综合评分 (等权)
        result["composite_score"] = (
            result["factor_momentum"]
            + result["factor_reversion"]
            + result["factor_volume"]
        )

        # 信号: 1=买入, -1=卖出, 0=持有
        result["signal"] = 0
        result.loc[result["composite_score"] > self.buy_threshold, "signal"] = 1
        result.loc[result["composite_score"] < self.sell_threshold, "signal"] = -1

        self._signals = result
        return result
