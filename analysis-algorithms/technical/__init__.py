"""
技术指标模块 — 适配新数据架构

所有函数接收标准 DataFrame (date, open, high, low, close, volume)，
返回添加指标列的 DataFrame。

数据来源优先级:
  1. Spark 预计算结果 (MySQL precomputed_* 表)
  2. 本地 Pandas 计算（此模块）

使用方式:
  from technical import MA, MACD, RSI, BollingerBands, KDJ

  kline = load_kline("000001")
  ma_df = MA(kline)
  macd_df = MACD(kline)
"""

from .ma import MA, ma_cross_signal
from .macd import MACD, macd_signal
from .rsi import RSI, rsi_signal
from .bollinger import BollingerBands, bollinger_signal
from .kdj import KDJ
