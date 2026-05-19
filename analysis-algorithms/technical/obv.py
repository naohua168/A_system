"""
OBV 指标 — 能量潮 (On-Balance Volume)

  - OBV: 累计成交量，当日收盘价上涨加成交量，下跌减成交量
  - obv_ma: OBV 均线（用于判断趋势）
  - obv_signal: OBV 突破/跌破均线的信号
"""
import pandas as pd
import numpy as np


def OBV(df: pd.DataFrame, ma_window: int = 20) -> pd.DataFrame:
    """计算 OBV 指标

    Args:
        df: K线数据 (需含 close, volume 列)
        ma_window: OBV均线窗口, 默认20
    Returns:
        添加 OBV, obv_ma, obv_signal 列的 DataFrame
    """
    result = df.copy()
    has_data = all(c in result.columns for c in ["close", "volume"])

    if not has_data:
        result["OBV"] = 0
        result["obv_ma"] = 0.0
        result["obv_signal"] = 0
        return result

    # 价格变动方向
    price_change = result["close"].diff()
    direction = np.sign(price_change)  # 1 上涨, -1 下跌, 0 持平

    # OBV = 累计(方向 × 成交量)
    result["OBV"] = (direction * result["volume"]).fillna(0).astype("int64").cumsum()
    result["obv_ma"] = result["OBV"].rolling(window=ma_window, min_periods=1).mean().fillna(0)

    # 信号: OBV 上穿 MA → 1 (价量配合), 下穿 MA → -1 (价量背离)
    result["obv_signal"] = 0
    obv_above = result["OBV"] > result["obv_ma"]
    obv_above_prev = obv_above.shift(1).fillna(False)
    result.loc[obv_above & ~obv_above_prev, "obv_signal"] = 1    # 金叉
    result.loc[~obv_above & obv_above_prev, "obv_signal"] = -1   # 死叉

    return result
