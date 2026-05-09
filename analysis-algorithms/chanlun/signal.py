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
from .segment import identify_segments
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from utils.data_loader import load_csv


@dataclass
class TradeSignal:
    """买卖信号"""
    signal_type: str       # "buy_1"/"buy_2"/"buy_3"/"sell_1"/"sell_2"/"sell_3"
    date: str
    price: float
    strength: float = 0.0  # 信号强度 (0~100)
    description: str = ""


def generate_signals(df: pd.DataFrame) -> List[TradeSignal]:
    """生成缠论买卖信号
    Args:
        df: K线数据
    Returns:
        买卖信号列表
    """
    signals = []

    # 1. 获取中枢和分型数据
    merged = None  # 在 identify_fractals 内部处理了
    fractal_df = identify_fractals(df)
    pen_df = identify_pens(df)
    central_df = identify_centrals(df)

    # 提取最后的中枢
    last_central_zg = 0.0
    last_central_zd = 0.0
    valid_central = central_df[central_df["central_ZG"] > 0]
    if not valid_central.empty:
        last_row = valid_central.iloc[-1]
        last_central_zg = last_row["central_ZG"]
        last_central_zd = last_row["central_ZD"]

    if last_central_zg == 0:
        return signals  # 无中枢，无法产生信号

    # 2. 提取分型点
    top_fractals = fractal_df[fractal_df["fractal_type"] == "top"]
    bottom_fractals = fractal_df[fractal_df["fractal_type"] == "bottom"]

    # 3. 判断买卖点
    for _, row in bottom_fractals.iterrows():
        price = row["fractal_price"]
        date = row["date"]

        # 第一类买点: 中枢下方
        if price < last_central_zd:
            strength = min(100, round((last_central_zd - price) / last_central_zd * 100, 1))
            signals.append(TradeSignal(
                signal_type="buy_1",
                date=str(date),
                price=price,
                strength=strength,
                description=f"第一类买点: 价格{price} 跌破中枢下轨{last_central_zd}",
            ))
        # 第二类买点: 中枢内部
        elif last_central_zd <= price <= last_central_zg:
            signals.append(TradeSignal(
                signal_type="buy_2",
                date=str(date),
                price=price,
                strength=40,
                description=f"第二类买点: 价格{price} 在中枢区间 [{last_central_zd}, {last_central_zg}] 内",
            ))
        # 第三类买点: 突破后回调不进中枢
        elif price < last_central_zg * 1.05:  # 略高于中枢
            signals.append(TradeSignal(
                signal_type="buy_3",
                date=str(date),
                price=price,
                strength=60,
                description=f"第三类买点: 价格{price} 回调未进入中枢",
            ))

    for _, row in top_fractals.iterrows():
        price = row["fractal_price"]
        date = row["date"]

        # 第一类卖点: 中枢上方
        if price > last_central_zg:
            strength = min(100, round((price - last_central_zg) / last_central_zg * 100, 1))
            signals.append(TradeSignal(
                signal_type="sell_1",
                date=str(date),
                price=price,
                strength=strength,
                description=f"第一类卖点: 价格{price} 突破中枢上轨{last_central_zg}",
            ))
        # 第二类卖点: 中枢内部
        elif last_central_zd <= price <= last_central_zg:
            signals.append(TradeSignal(
                signal_type="sell_2",
                date=str(date),
                price=price,
                strength=40,
                description=f"第二类卖点: 价格{price} 在中枢区间内",
            ))
        # 第三类卖点: 跌破后回调不进中枢
        elif price > last_central_zd * 0.95:
            signals.append(TradeSignal(
                signal_type="sell_3",
                date=str(date),
                price=price,
                strength=60,
                description=f"第三类卖点: 价格{price} 反弹未进入中枢",
            ))

    return signals
