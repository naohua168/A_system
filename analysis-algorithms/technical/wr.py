"""
W%R 指标 — 威廉指标 (Williams %R)

  - W%R: 衡量收盘价在过去N天价格区间中的位置
  - 值域 [-100, 0]:
    - -80 ~ -100: 超卖 (买入信号)
    - -20 ~ 0:    超买 (卖出信号)
"""
import pandas as pd
import numpy as np


def WPR(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """计算威廉 %R 指标

    Args:
        df: K线数据 (需含 high, low, close 列)
        window: 周期数, 默认14
    Returns:
        添加 WPR, wr_signal 列的 DataFrame
    """
    result = df.copy()
    has_data = all(c in result.columns for c in ["high", "low", "close"])

    if not has_data:
        result["WPR"] = 0.0
        result["wr_signal"] = 0
        return result

    # HH = N日最高价的最高值, LL = N日最低价的最低值
    hh = result["high"].rolling(window=window, min_periods=1).max()
    ll = result["low"].rolling(window=window, min_periods=1).min()

    # W%R = (HH - Close) / (HH - LL) * -100
    denom = hh - ll
    result["WPR"] = np.where(
        denom > 0,
        ((hh - result["close"]) / denom * -100).round(2),
        0.0,
    )

    # 信号: <= -80 超卖, >= -20 超买
    result["wr_signal"] = 0
    result.loc[result["WPR"] <= -80, "wr_signal"] = 1    # 超卖 → 买入信号
    result.loc[result["WPR"] >= -20, "wr_signal"] = -1   # 超买 → 卖出信号

    return result
