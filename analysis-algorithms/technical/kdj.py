"""KDJ — 全向量化，消除 Python 循环"""
import pandas as pd
import numpy as np


def KDJ(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """KDJ — 全向量化实现 (0 Python for-loops)

    K = EWMA(RSV, alpha=1/m1)   初始值50
    D = EWMA(K, alpha=1/m2)     初始值50
    J = 3K - 2D
    """
    result = df.copy()

    # RSV（向量化）
    low_n = result["low"].rolling(window=n).min()
    high_n = result["high"].rolling(window=n).max()
    denom = (high_n - low_n).replace(0, np.nan)
    rsv = ((result["close"] - low_n) / denom * 100).fillna(50)

    # K = EWMA(RSV, alpha=1/3) 初始值50
    result["K"] = rsv.ewm(alpha=1 / m1, adjust=False).mean().round(2)
    # 前 n-1 行置为 50（标准KDJ从第n行开始）
    result["K"].iloc[:n - 1] = 50.0

    # D = EWMA(K, alpha=1/3)
    result["D"] = result["K"].ewm(alpha=1 / m2, adjust=False).mean().round(2)
    result["D"].iloc[:n - 1] = 50.0

    # J = 3K - 2D
    result["J"] = (3 * result["K"] - 2 * result["D"]).round(2)

    result["kdj_overbought"] = result["K"] > 80
    result["kdj_oversold"] = result["K"] < 20
    return result
