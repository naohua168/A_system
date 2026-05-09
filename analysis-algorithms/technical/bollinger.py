"""
布林带 (Bollinger Bands)
中轨 = MA20, 上轨 = 中轨 + 2σ, 下轨 = 中轨 - 2σ
"""

import pandas as pd
import numpy as np


def BollingerBands(df: pd.DataFrame, period: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    """计算布林带
    Args:
        df: 必须包含 'close' 列
        period: 中轨周期 (默认20)
        std_mult: 标准差倍数 (默认2)
    Returns:
        添加 BOLL_MID, BOLL_UP, BOLL_DOWN, BOLL_WIDTH 列的 DataFrame
    """
    result = df.copy()
    close = result["close"]

    result["BOLL_MID"] = close.rolling(window=period).mean().round(2)
    boll_std = close.rolling(window=period).std(ddof=0)  # 总体标准差
    result["BOLL_UP"] = (result["BOLL_MID"] + std_mult * boll_std).round(2)
    result["BOLL_DOWN"] = (result["BOLL_MID"] - std_mult * boll_std).round(2)

    # 带宽 = (上轨 - 下轨) / 中轨 × 100% (防除零)
    mid_safe = result["BOLL_MID"].replace(0, np.nan)
    result["BOLL_WIDTH"] = (
        (result["BOLL_UP"] - result["BOLL_DOWN"]) / mid_safe * 100
    ).round(2)

    # %B = (收盘价 - 下轨) / (上轨 - 下轨) (防除零)
    band_range = (result["BOLL_UP"] - result["BOLL_DOWN"]).replace(0, np.nan)
    result["BOLL_PB"] = (
        (close - result["BOLL_DOWN"]) / band_range
    ).fillna(0.5).round(4)

    return result


def bollinger_signal(df: pd.DataFrame) -> pd.DataFrame:
    """布林带信号
    - 价格触及上轨: 超买
    - 价格触及下轨: 超卖
    - 带宽收窄: 可能变盘
    """
    result = df.copy()
    result["boll_upper_touch"] = result["close"] >= result["BOLL_UP"]
    result["boll_lower_touch"] = result["close"] <= result["BOLL_DOWN"]

    return result
