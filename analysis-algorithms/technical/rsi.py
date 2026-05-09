"""
RSI 相对强弱指标 (Relative Strength Index)
RSI6, RSI12, RSI24 — 衡量价格变动速度和幅度
"""

import pandas as pd


def RSI(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    """计算 RSI 指标
    Args:
        df: 必须包含 'close' 列
        periods: 周期列表，默认 [6, 12, 24]
    Returns:
        添加 RSI{period} 列的 DataFrame
    """
    if periods is None:
        periods = [6, 12, 24]

    result = df.copy()
    delta = result["close"].diff()

    for p in periods:
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.rolling(window=p, min_periods=p).mean()
        avg_loss = loss.rolling(window=p, min_periods=p).mean()

        # 使用 Wilder 平滑 (SMMA)
        # avg_gain_t = (avg_gain_{t-1} × (p-1) + gain_t) / p
        for i in range(p * 2, len(result)):
            avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (p - 1) + gain.iloc[i]) / p
            avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (p - 1) + loss.iloc[i]) / p

        rs = avg_gain / avg_loss
        result[f"RSI{p}"] = (100 - (100 / (1 + rs))).round(2)

    return result


def rsi_signal(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI 信号
    - RSI > 70: 超买 (可能回调)
    - RSI < 30: 超卖 (可能反弹)
    """
    result = df.copy()
    rsi_col = f"RSI{period}"

    result["rsi_overbought"] = result[rsi_col] > 70
    result["rsi_oversold"] = result[rsi_col] < 30

    return result
