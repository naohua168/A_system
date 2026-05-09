"""
MACD 指标 (指数平滑移动平均线)
EMA12, EMA26, DIF, DEA, MACD 柱状图
"""

import pandas as pd


def MACD(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """计算 MACD 指标
    Args:
        df: 必须包含 'close' 列
        fast: 快线周期 (默认12)
        slow: 慢线周期 (默认26)
        signal: 信号线周期 (默认9)
    Returns:
        添加 EMA12, EMA26, DIF, DEA, MACD 列的 DataFrame
    """
    result = df.copy()
    close = result["close"]

    # EMA 计算 (使用 ewm)
    result["EMA12"] = close.ewm(span=fast, adjust=False).mean().round(4)
    result["EMA26"] = close.ewm(span=slow, adjust=False).mean().round(4)

    # DIF = EMA12 - EMA26
    result["DIF"] = (result["EMA12"] - result["EMA26"]).round(4)

    # DEA = DIF 的 9 日 EMA
    result["DEA"] = result["DIF"].ewm(span=signal, adjust=False).mean().round(4)

    # MACD 柱 = (DIF - DEA) × 2
    result["MACD"] = ((result["DIF"] - result["DEA"]) * 2).round(4)

    return result


def macd_signal(df: pd.DataFrame) -> pd.DataFrame:
    """MACD 买卖信号
    - 金叉: DIF 上穿 DEA (0轴上方为强势金叉)
    - 死叉: DIF 下穿 DEA
    - 底背离: 价格新低但 DIF 未新低
    - 顶背离: 价格新高但 DIF 未新高
    """
    result = df.copy()

    # DIF/DEA 交叉: diff() 返回 1(上穿), -1(下穿), 0(不变)
    result["dif_above_dea"] = result["DIF"] > result["DEA"]
    result["macd_cross"] = result["dif_above_dea"].diff()
    result.loc[result["macd_cross"] == 1, "macd_signal_str"] = "golden_cross"
    result.loc[result["macd_cross"] == -1, "macd_signal_str"] = "death_cross"

    return result
