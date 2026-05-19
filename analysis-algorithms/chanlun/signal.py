"""
缠论 — 买卖信号判断

三类买点:
  第一类买点: 中枢下轨下方的底分型 (趋势背驰)
  第二类买点: 中枢内部的底分型 (回调不破ZD)
  第三类买点: 突破中枢后回调不进入中枢的底分型

三类卖点:
  第一类卖点: 中枢上轨上方的顶分型
  第二类卖点: 中枢内部的顶分型
  第三类卖点: 跌破中枢后反弹不进入中枢的顶分型
"""

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from .fractal import Fractal, identify_fractals
from .central import Central, identify_centrals
from .pen import identify_pens
from data.loader import load_csv


@dataclass
class TradeSignal:
    """买卖信号"""
    signal_type: str       # "buy_1"/"buy_2"/"buy_3"/"sell_1"/"sell_2"/"sell_3"
    date: str
    price: float
    strength: float = 0.0  # 信号强度 (0~100)
    description: str = ""


def _get_active_central(central_df: pd.DataFrame, fractal_date: str) -> tuple:
    """获取分型发生时活跃的中枢区间

    遍历历史中枢，找到在 fractal_date 之前最后一个已形成的中枢。
    若无历史中枢，返回 (0, 0) 表示无中枢。
    """
    valid = central_df[central_df["central_ZG"] > 0]
    if valid.empty:
        return (0.0, 0.0)
    try:
        f_date = pd.Timestamp(fractal_date)
        before = valid[pd.to_datetime(valid["date"]) <= f_date]
        if before.empty:
            return (0.0, 0.0)
        row = before.iloc[-1]
        return (float(row["central_ZG"]), float(row["central_ZD"]))
    except Exception:
        row = valid.iloc[-1]
        return (float(row["central_ZG"]), float(row["central_ZD"]))


def generate_signals(df: pd.DataFrame) -> List[TradeSignal]:
    """生成缠论买卖信号

    若 df 已有 fractal_type / pen_direction / central_ZG 列，直接使用（避免重复计算）。
    否则从原始 K 线开始全流程计算。

    Args:
        df: K线数据（可已附带缠论分析列）
    Returns:
        买卖信号列表
    """
    signals = []

    # 1. 获取中枢和分型数据（如果尚未计算）
    if "fractal_type" in df.columns:
        fractal_df = df
    else:
        fractal_df = identify_fractals(df)

    if "pen_direction" in df.columns:
        pen_df = df
    else:
        pen_df = identify_pens(df)

    if "central_ZG" in df.columns:
        central_df = df
    else:
        central_df = identify_centrals(df)

    # 2. 提取分型点
    top_fractals = fractal_df[fractal_df["fractal_type"] == "top"]
    bottom_fractals = fractal_df[fractal_df["fractal_type"] == "bottom"]

    # 3. 判断买卖点（遍历每个分型，匹配当时活跃的中枢）
    for _, row in bottom_fractals.iterrows():
        price = row["fractal_price"]
        fdate = row["date"]
        zg, zd = _get_active_central(central_df, fdate)
        if zg == 0:
            continue  # 无活跃中枢，跳过

        if price < zd:  # 第一类买点: 中枢下方
            strength = min(100, round((zd - price) / zd * 100, 1))
            signals.append(TradeSignal(
                signal_type="buy_1", date=str(fdate), price=price,
                strength=strength,
                description=f"第一类买点: 价格{price} 跌破中枢下轨{zd}",
            ))
        elif zd <= price <= zg:  # 第二类买点: 中枢内部
            signals.append(TradeSignal(
                signal_type="buy_2", date=str(fdate), price=price,
                strength=40,
                description=f"第二类买点: 价格{price} 在中枢区间 [{zd}, {zg}] 内",
            ))
        elif price < zg * 1.05:  # 第三类买点
            signals.append(TradeSignal(
                signal_type="buy_3", date=str(fdate), price=price,
                strength=60,
                description=f"第三类买点: 价格{price} 回调未进入中枢",
            ))

    for _, row in top_fractals.iterrows():
        price = row["fractal_price"]
        fdate = row["date"]
        zg, zd = _get_active_central(central_df, fdate)
        if zg == 0:
            continue

        if price > zg:  # 第一类卖点
            strength = min(100, round((price - zg) / zg * 100, 1))
            signals.append(TradeSignal(
                signal_type="sell_1", date=str(fdate), price=price,
                strength=strength,
                description=f"第一类卖点: 价格{price} 突破中枢上轨{zg}",
            ))
        elif zd <= price <= zg:  # 第二类卖点
            signals.append(TradeSignal(
                signal_type="sell_2", date=str(fdate), price=price,
                strength=40,
                description=f"第二类卖点: 价格{price} 在中枢区间内",
            ))
        elif price > zd * 0.95:  # 第三类卖点
            signals.append(TradeSignal(
                signal_type="sell_3", date=str(fdate), price=price,
                strength=60,
                description=f"第三类卖点: 价格{price} 反弹未进入中枢",
            ))

    return signals
