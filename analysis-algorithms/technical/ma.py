"""
移动平均线 (MA)
MA5, MA10, MA20, MA60 — 识别趋势方向
"""

import pandas as pd


def MA(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    """计算移动平均线
    Args:
        df: 必须包含 'close' 列
        periods: 周期列表，默认 [5, 10, 20, 60]
    Returns:
        添加 MA{period} 列的 DataFrame
    """
    if periods is None:
        periods = [5, 10, 20, 60]

    result = df.copy()
    for p in periods:
        result[f"MA{p}"] = result["close"].rolling(window=p).mean().round(2)

    return result


def ma_cross_signal(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> pd.DataFrame:
    """均线交叉信号
    - 金叉: 短线上穿长线 → 买入信号 (1)
    - 死叉: 短线下穿长线 → 卖出信号 (-1)
    """
    result = df.copy()
    result["MA_fast"] = result["close"].rolling(fast).mean()
    result["MA_slow"] = result["close"].rolling(slow).mean()

    result["signal"] = 0
    result.loc[result["MA_fast"] > result["MA_slow"], "signal"] = 1
    result.loc[result["MA_fast"] < result["MA_slow"], "signal"] = -1

    # 找出交叉点
    result["cross"] = result["signal"].diff()
    result.loc[result["cross"] == 2, "cross_signal"] = "golden_cross"
    result.loc[result["cross"] == -2, "cross_signal"] = "death_cross"

    return result
