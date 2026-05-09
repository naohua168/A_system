"""
缠论 — 中枢识别

中枢 = 连续 3 段重叠的区域
  - ZG (中枢高) = 三段上限的最小值
  - ZD (中枢低) = 三段下限的最大值
  - ZF (中枢区间) = ZG - ZD

突破中枢上轨(ZG) → 可能上涨
跌破中枢下轨(ZD) → 可能下跌
"""

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from .segment import Segment, find_segments, identify_segments
from .pen import identify_pens, find_pens
from .fractal import find_fractals, filter_fractals, merge_klines


@dataclass
class Central:
    """中枢"""
    segments: List[Segment]   # 构成中枢的3段
    ZG: float                 # 中枢高 (上限最小值)
    ZD: float                 # 中枢低 (下限最大值)
    ZF: float                 # 中枢区间宽度
    start_date: str
    end_date: str
    mid_price: float = 0.0    # 中枢中轴

    @property
    def is_valid(self) -> bool:
        return self.ZG > self.ZD


def find_centrals(segments: List[Segment]) -> List[Central]:
    """识别中枢：3段连续重叠区域

    中枢区间 = [ZD, ZG]
    ZD = max(三段的下限)
    ZG = min(三段的上限)
    """
    if len(segments) < 3:
        return []

    centrals = []
    for i in range(len(segments) - 2):
        s1, s2, s3 = segments[i], segments[i + 1], segments[i + 2]

        # 三段的上限和下限
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

        ZG = min(highs)  # 上限最小值
        ZD = max(lows)   # 下限最大值

        if ZG > ZD:  # 有效中枢
            central = Central(
                segments=[s1, s2, s3],
                ZG=round(ZG, 2),
                ZD=round(ZD, 2),
                ZF=round(ZG - ZD, 2),
                start_date=s1.start_date,
                end_date=s3.end_date,
                mid_price=round((ZG + ZD) / 2, 2),
            )
            centrals.append(central)

    return centrals


def identify_centrals(df: pd.DataFrame) -> pd.DataFrame:
    """完整的中枢识别流程"""
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

    for central in centrals:
        start_idx = central.segments[0].pens[0].start_fractal.k2.idx
        end_idx = central.segments[-1].pens[-1].end_fractal.k2.idx
        for idx in range(start_idx, end_idx + 1):
            if idx < len(result):
                result.loc[result.index[idx], "central_ZG"] = central.ZG
                result.loc[result.index[idx], "central_ZD"] = central.ZD
                result.loc[result.index[idx], "central_ZF"] = central.ZF
                result.loc[result.index[idx], "central_mid"] = central.mid_price

    return result
