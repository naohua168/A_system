"""
KDJ 随机指标 (Stochastic Oscillator)
K值、D值、J值 — 判断超买超卖
"""

import pandas as pd
import numpy as np


def KDJ(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """计算 KDJ 指标
    Args:
        df: 必须包含 high, low, close 列
        n: RSV 周期 (默认9)
        m1: K 值平滑 (默认3)
        m2: D 值平滑 (默认3)
    Returns:
        添加 RSV, K, D, J 列的 DataFrame
    """
    result = df.copy()

    # RSV = (收盘价 - N日内最低) / (N日内最高 - N日内最低) × 100
    low_n = result["low"].rolling(window=n).min()
    high_n = result["high"].rolling(window=n).max()

    # 防止除零: 一字板时 high_n == low_n, RSV 设为 50
    denom = (high_n - low_n).replace(0, np.nan)
    result["RSV"] = ((result["close"] - low_n) / denom * 100).fillna(50).round(2)

    # K = 2/3 × 前一日K + 1/3 × RSV
    result["K"] = 50.0
    result["D"] = 50.0

    for i in range(n, len(result)):
        rsv = result.loc[result.index[i], "RSV"]
        prev_k = result.loc[result.index[i - 1], "K"]
        prev_d = result.loc[result.index[i - 1], "D"]

        k_val = 2 / 3 * prev_k + 1 / 3 * rsv
        d_val = 2 / 3 * prev_d + 1 / 3 * k_val
        j_val = 3 * k_val - 2 * d_val

        result.loc[result.index[i], "K"] = round(k_val, 2)
        result.loc[result.index[i], "D"] = round(d_val, 2)
        result.loc[result.index[i], "J"] = round(j_val, 2)

    # 信号判断
    result["kdj_overbought"] = result["K"] > 80  # 超买
    result["kdj_oversold"] = result["K"] < 20     # 超卖

    return result
