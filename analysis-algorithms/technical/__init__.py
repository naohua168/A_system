# analysis-algorithms/technical - 技术指标计算模块
# 所有指标接收 DataFrame (列: date, open, high, low, close, volume)
# 返回 DataFrame (原始列 + 指标列)

import pandas as pd

from .ma import MA
from .macd import MACD
from .kdj import KDJ
from .rsi import RSI
from .bollinger import BollingerBands


def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """一键计算所有技术指标"""
    df = MA(df)
    df = MACD(df)
    df = KDJ(df)
    df = RSI(df)
    df = BollingerBands(df)
    return df
