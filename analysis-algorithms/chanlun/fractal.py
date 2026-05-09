"""
缠论 — 分型识别
核心步骤:
  1. K线包含处理（合并相邻包含关系的K线）
  2. 顶分型识别: 连续3根处理后K线, 中间高点最高(↑↓↑)
  3. 底分型识别: 连续3根处理后K线, 中间低点最低(↓↑↓)

包含处理规则:
  - 上升趋势(后一K线高点高于前一K线高点): 取高高 (高点取最高, 低点取最高)
  - 下降趋势(后一K线低点低于前一K线低点): 取低低 (高点取最低, 低点取最低)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class KLine:
    """处理后的K线"""
    date: str
    high: float
    low: float
    idx: int = 0  # 原始K线索引

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2


@dataclass
class Fractal:
    """分型"""
    type: str           # "top" 顶分型 / "bottom" 底分型
    k1: KLine           # 第1根K线
    k2: KLine           # 第2根K线 (分型顶点)
    k3: KLine           # 第3根K线
    strength: float = 0.0  # 分型强度

    @property
    def date(self) -> str:
        return self.k2.date

    @property
    def price(self) -> float:
        return self.k2.high if self.type == "top" else self.k2.low


def merge_klines(df: pd.DataFrame) -> List[KLine]:
    """K线包含处理 — 合并有包含关系的相邻K线
    Args:
        df: 包含 date, high, low 列的 DataFrame，按日期升序
    Returns:
        处理后的 KLine 列表
    """
    if df.empty:
        return []

    klines = [
        KLine(
            date=str(row["date"]) if not isinstance(row["date"], str)
                 else row["date"],
            high=float(row["high"]),
            low=float(row["low"]),
            idx=i,
        )
        for i, (_, row) in enumerate(df.iterrows())
    ]

    if len(klines) <= 1:
        return klines

    merged = [klines[0]]

    for i in range(1, len(klines)):
        curr = klines[i]
        prev = merged[-1]

        # 判断是否包含: 前包含后 或 后包含前
        # 包含条件: curr.high <= prev.high and curr.low >= prev.low (前包含后)
        #          或 curr.high >= prev.high and curr.low <= prev.low (后包含前)
        is_contained = (curr.high <= prev.high and curr.low >= prev.low) or \
                       (curr.high >= prev.high and curr.low <= prev.low)

        if not is_contained:
            merged.append(curr)
            continue

        # 判断趋势方向: 取 merged 中倒数第二根判断
        if len(merged) >= 2:
            prev2 = merged[-2]
            is_up_trend = prev.high > prev2.high  # 上升趋势
        else:
            # 只有一根K线时，用当前K线判断
            is_up_trend = curr.high > prev.high

        if is_up_trend:
            # 上升趋势: 取高高 (高点取最高, 低点取最高)
            merged[-1] = KLine(
                date=prev.date,
                high=max(prev.high, curr.high),
                low=max(prev.low, curr.low),
                idx=prev.idx,
            )
        else:
            # 下降趋势: 取低低 (高点取最低, 低点取最低)
            merged[-1] = KLine(
                date=curr.date if curr.high > prev.high else prev.date,
                high=min(prev.high, curr.high),
                low=min(prev.low, curr.low),
                idx=prev.idx if prev.high < curr.high else curr.idx,
            )

    return merged


def _calc_strength(k1: KLine, k2: KLine, k3: KLine, ftype: str) -> float:
    """计算分型强度"""
    if ftype == "top":
        # 顶分型强度 = (k2高点 - k1高点) + (k2高点 - k3高点)
        return (k2.high - k1.high) + (k2.high - k3.high)
    else:
        # 底分型强度 = (k1低点 - k2低点) + (k3低点 - k2低点)
        return (k1.low - k2.low) + (k3.low - k2.low)


def find_fractals(klines: List[KLine]) -> List[Fractal]:
    """识别顶底分型
    规则: 连续3根处理后K线
      - 顶分型: 中间高点 > 左右高点 (↑↓↑)
      - 底分型: 中间低点 < 左右低点 (↓↑↓)
    """
    if len(klines) < 3:
        return []

    fractals = []

    for i in range(1, len(klines) - 1):
        k1, k2, k3 = klines[i - 1], klines[i], klines[i + 1]

        # 顶分型: 中间最高价最高, 中间最低价也最高
        if k2.high > k1.high and k2.high > k3.high and \
           k2.low > k1.low and k2.low > k3.low:
            f = Fractal(
                type="top",
                k1=k1, k2=k2, k3=k3,
                strength=round(_calc_strength(k1, k2, k3, "top"), 2),
            )
            fractals.append(f)

        # 底分型: 中间最低价最低, 中间最高价也最低
        elif k2.low < k1.low and k2.low < k3.low and \
             k2.high < k1.high and k2.high < k3.high:
            f = Fractal(
                type="bottom",
                k1=k1, k2=k2, k3=k3,
                strength=round(_calc_strength(k1, k2, k3, "bottom"), 2),
            )
            fractals.append(f)

    return fractals


def filter_fractals(fractals: List[Fractal]) -> List[Fractal]:
    """过滤分型: 交替出现 + 间隔至少1根K线"""
    if not fractals:
        return []

    filtered = [fractals[0]]

    for f in fractals[1:]:
        last = filtered[-1]

        # 分型必须交替: 顶底/底顶
        if f.type == last.type:
            continue

        # 间隔至少1根K线
        if abs(f.k2.idx - last.k2.idx) < 2:
            continue

        filtered.append(f)

    return filtered


def identify_fractals(df: pd.DataFrame) -> pd.DataFrame:
    """完整的分型识别流程: 包含处理 → 分型识别 → 过滤
    Args:
        df: K线数据 (date, high, low, close)
    Returns:
        带分型标记的 DataFrame (fractal_type, fractal_price)
    """
    # 1. K线包含处理
    merged = merge_klines(df)

    # 2. 分型识别
    all_fractals = find_fractals(merged)

    # 3. 分型过滤
    filtered = filter_fractals(all_fractals)

    # 4. 映射回原始K线
    result = df.copy()
    result["fractal_type"] = ""
    result["fractal_price"] = 0.0
    result["fractal_strength"] = 0.0

    for f in filtered:
        idx = f.k2.idx
        if idx < len(result):
            result.loc[result.index[idx], "fractal_type"] = f.type
            result.loc[result.index[idx], "fractal_price"] = f.price
            result.loc[result.index[idx], "fractal_strength"] = f.strength

    return result
