"""
CCI 指标 — 商品通道指数 (Commodity Channel Index)

  - CCI: 衡量价格相对于统计均值的偏离程度
  - cci_signal: +100 超买阈值, -100 超卖阈值
"""
import pandas as pd
import numpy as np


def CCI(df: pd.DataFrame, window: int = 20, constant: float = 0.015) -> pd.DataFrame:
    """计算 CCI 指标

    Args:
        df: K线数据 (需含 high, low, close 列)
        window: 周期数, 默认20
        constant: 常数, 默认0.015
    Returns:
        添加 CCI, cci_signal 列的 DataFrame
    """
    result = df.copy()
    has_data = all(c in result.columns for c in ["high", "low", "close"])

    if not has_data:
        result["CCI"] = 0.0
        result["cci_signal"] = 0
        return result

    # TP = (H + L + C) / 3
    tp = (result["high"] + result["low"] + result["close"]) / 3.0
    sma = tp.rolling(window=window, min_periods=1).mean()

    # Mean Deviation (平均绝对偏差)
    mad = tp.rolling(window=window, min_periods=1).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    ).fillna(0)

    # CCI = (TP - SMA) / (0.015 * MD)
    result["CCI"] = np.where(
        mad > 0,
        ((tp - sma) / (constant * mad)).round(2),
        0.0,
    )

    # 信号: +100 超买, -100 超卖
    result["cci_signal"] = 0
    result.loc[result["CCI"] > 100, "cci_signal"] = 1
    result.loc[result["CCI"] < -100, "cci_signal"] = -1

    return result
