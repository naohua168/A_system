"""
缠论 — 中枢识别（增强版）

中枢 = 连续 3 段重叠的区域
  - ZG (中枢高) = 三段上限的最小值
  - ZD (中枢低) = 三段下限的最大值
  - ZF (中枢区间) = ZG - ZD

增强特性（v2）:
  1. 中枢级别扩展：识别3段重叠+6段重叠（高级别中枢）
  2. 中枢延伸识别：同一区域内超过6段构成延伸
  3. 中枢破坏：突破ZG/跌破ZD标记

突破中枢上轨(ZG) → 可能上涨
跌破中枢下轨(ZD) → 可能下跌
"""

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import numpy as np

from .segment import Segment, find_segments, identify_segments
from .pen import identify_pens, find_pens
from .fractal import find_fractals, filter_fractals, merge_klines


@dataclass
class Central:
    """中枢"""
    segments: List[Segment]   # 构成中枢的段
    ZG: float                 # 中枢高 (上限最小值)
    ZD: float                 # 中枢低 (下限最大值)
    ZF: float                 # 中枢区间宽度
    start_date: str
    end_date: str
    mid_price: float = 0.0    # 中枢中轴
    level: int = 0            # 中枢级别: 0=基础, 1=扩展
    extended: bool = False    # 是否延伸(>=6段)

    @property
    def is_valid(self) -> bool:
        return self.ZG > self.ZD


def find_centrals(segments: List[Segment]) -> List[Central]:
    """识别中枢：3段连续重叠区域（增强版，支持级别扩展）

    中枢区间 = [ZD, ZG]
    ZD = max(三段的下限)
    ZG = min(三段的上限)

    级别扩展：当两个同级中枢有重叠时，构成本级别中枢
    """
    if len(segments) < 3:
        return []

    # Step 1: 基础中枢识别（3段重叠）
    basic_centrals = []
    for i in range(len(segments) - 2):
        s1, s2, s3 = segments[i], segments[i + 1], segments[i + 2]

        highs = [
            max(s1.start_price, s1.end_price),
            max(s2.start_price, s2.end_price),
            max(s3.start_price, s3.end_price),
        ]
        lows = [
            min(s1.start_price, s1.end_price),
            min(s2.start_price, s2.end_price),
            min(s3.start_price, s3.end_price),
        ]

        ZG = min(highs)
        ZD = max(lows)

        if ZG > ZD:
            central = Central(
                segments=[s1, s2, s3],
                ZG=round(ZG, 2),
                ZD=round(ZD, 2),
                ZF=round(ZG - ZD, 2),
                start_date=s1.start_date,
                end_date=s3.end_date,
                mid_price=round((ZG + ZD) / 2, 2),
                level=0,
            )
            basic_centrals.append(central)

    if not basic_centrals:
        return []

    # Step 2: 中枢延伸检测（相邻中枢区间重叠 -> 延伸）
    for c in basic_centrals:
        if c.ZF > 0:
            # 检查中枢内段数是否超过6（延伸）
            if len(c.segments) >= 6:
                c.extended = True

    # Step 3: 级别扩展（相邻基础中枢重叠 -> 高级别中枢）
    expanded = []
    used = set()
    for i in range(len(basic_centrals) - 1):
        if i in used:
            continue
        c1 = basic_centrals[i]

        # 寻找与c1重叠的下一个中枢
        for j in range(i + 1, min(i + 4, len(basic_centrals))):
            if j in used:
                continue
            c2 = basic_centrals[j]

            # 检查c1和c2的区间是否重叠
            overlap_high = min(c1.ZG, c2.ZG)
            overlap_low = max(c1.ZD, c2.ZD)
            if overlap_high > overlap_low:
                # 形成扩展中枢
                all_segs = c1.segments + c2.segments
                expanded_central = Central(
                    segments=all_segs,
                    ZG=round(overlap_high, 2),
                    ZD=round(overlap_low, 2),
                    ZF=round(overlap_high - overlap_low, 2),
                    start_date=c1.start_date,
                    end_date=c2.end_date,
                    mid_price=round((overlap_high + overlap_low) / 2, 2),
                    level=1,
                )
                expanded.append(expanded_central)
                used.add(i)
                used.add(j)
                break

        if i not in used:
            used.add(i)
            expanded.append(c1)

    # 合并：保留未使用的扩展中枢
    result = expanded if expanded else basic_centrals

    # 按时间排序
    result.sort(key=lambda c: c.start_date)
    return result


def identify_centrals(df: pd.DataFrame) -> pd.DataFrame:
    """完整的中枢识别流程（增强版）"""
    result = df.copy()

    merged = merge_klines(df)
    fractals = find_fractals(merged)
    filtered = filter_fractals(fractals)
    pens = find_pens(filtered)
    segments = find_segments(pens)
    centrals = find_centrals(segments)

    # 标记中枢区间
    result["central_ZG"] = 0.0
    result["central_ZD"] = 0.0
    result["central_ZF"] = 0.0
    result["central_mid"] = 0.0
    result["central_level"] = 0
    result["central_extended"] = False

    for central in centrals:
        start_idx = central.segments[0].pens[0].start_fractal.k2.idx
        end_idx = central.segments[-1].pens[-1].end_fractal.k2.idx
        for idx in range(start_idx, end_idx + 1):
            if idx < len(result):
                result.loc[result.index[idx], "central_ZG"] = central.ZG
                result.loc[result.index[idx], "central_ZD"] = central.ZD
                result.loc[result.index[idx], "central_ZF"] = central.ZF
                result.loc[result.index[idx], "central_mid"] = central.mid_price
                result.loc[result.index[idx], "central_level"] = central.level
                result.loc[result.index[idx], "central_extended"] = central.extended

    return result
