"""
成交量指标 — 成交量均线(VOL_MA) + 量比(Volume Ratio)

  - VOL_MA5: 5日均量
  - VOL_MA10: 10日均量
  - VOL_MA20: 20日均量
  - vol_ratio: 当日量 / 最近5日均量（量比 > 2 放量, < 0.5 缩量）
  - volume_signal: 放量(+) / 缩量(-) / 正常(0)
"""
import pandas as pd
import numpy as np


def VOLUME(df: pd.DataFrame, windows: list = None) -> pd.DataFrame:
    """计算成交量均线指标

    Args:
        df: K线数据 (需含 volume 列)
        windows: 均线窗口列表，默认 [5, 10, 20]
    Returns:
        添加 VOL_MA5, VOL_MA10, VOL_MA20, vol_ratio, volume_signal 列的 DataFrame
    """
    if windows is None:
        windows = [5, 10, 20]
    result = df.copy()

    if "volume" not in result.columns:
        result["VOL_MA5"] = 0
        result["VOL_MA10"] = 0
        result["VOL_MA20"] = 0
        result["vol_ratio"] = 0.0
        result["volume_signal"] = 0
        return result

    vol = result["volume"].replace(0, np.nan).fillna(method="ffill")

    # 成交量均线
    label_map = {5: "VOL_MA5", 10: "VOL_MA10", 20: "VOL_MA20"}
    for w in windows:
        col = label_map.get(w, f"VOL_MA{w}")
        result[col] = vol.rolling(window=w, min_periods=1).mean().fillna(0)

    # 量比 = 当日量 / 最近5日均量
    ma5 = result["VOL_MA5"]
    result["vol_ratio"] = np.where(ma5 > 0, (vol / ma5).round(2), 1.0)

    # 信号: 放量 > 2, 缩量 < 0.5
    result["volume_signal"] = 0
    result.loc[result["vol_ratio"] > 2.0, "volume_signal"] = 1    # 放量
    result.loc[result["vol_ratio"] < 0.5, "volume_signal"] = -1   # 缩量

    return result
