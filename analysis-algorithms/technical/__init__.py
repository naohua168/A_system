"""
技术指标模块 — 适配新数据架构

所有函数接收标准 DataFrame (date, open, high, low, close, volume)，
返回添加指标列的 DataFrame。

数据来源优先级:
  1. Spark 预计算结果 (MySQL precomputed_* 表)
  2. 本地 Pandas 计算（此模块）

使用方式:
  from technical import MA, MACD, RSI, BollingerBands, KDJ, VOLUME, CCI, WPR, OBV

  kline = load_kline("000001")
  ma_df = MA(kline)
  full_df = calculate_all(kline)  # 一键全部指标
"""

from .ma import MA, ma_cross_signal
from .macd import MACD, macd_signal
from .rsi import RSI, rsi_signal
from .bollinger import BollingerBands, bollinger_signal
from .kdj import KDJ
from .volume import VOLUME
from .cci import CCI
from .wr import WPR
from .obv import OBV

import pandas as pd


def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """一键计算全部技术指标 — 将9个指标叠加到同一DataFrame

    Args:
        df: K线数据 (date, open, high, low, close, volume)
    Returns:
        包含所有指标列的 DataFrame
    """
    result = df.copy()
    result = MA(result)
    result = MACD(result)
    result = KDJ(result)
    result = RSI(result)
    result = BollingerBands(result)
    result = VOLUME(result)
    result = CCI(result)
    result = WPR(result)
    result = OBV(result)
    return result
