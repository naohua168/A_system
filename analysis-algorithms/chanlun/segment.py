"""
缠论 — 线段识别

线段 = 至少 3 笔构成
在笔的基础上划分更高一级的趋势结构
"""

from dataclasses import dataclass
from typing import List

import pandas as pd

from .pen import Pen, identify_pens, find_pens
from .fractal import find_fractals, filter_fractals, merge_klines


@dataclass
class Segment:
    """线段"""
    direction: str       # "up" / "down"
    pens: List[Pen]      # 包含的笔列表
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    height: float = 0.0

    @property
    def pen_count(self) -> int:
        return len(self.pens)

    @property
    def change_pct(self) -> float:
        if self.start_price > 0:
            return round((self.end_price - self.start_price) / self.start_price * 100, 2)
        return 0.0


def find_segments(pens: List[Pen]) -> List[Segment]:
    """将笔组合为线段：至少 3 笔构成一线段"""
    if len(pens) < 3:
        return []

    segments = []
    i = 0
    while i <= len(pens) - 3:
        pen1, pen2, pen3 = pens[i], pens[i + 1], pens[i + 2]

        # 线段特征序列: 奇数笔的方向决定线段方向
        if pen1.direction == pen3.direction and \
           pen2.direction != pen1.direction:
            # 形成线段
            direction = pen1.direction
            seg = Segment(
                direction=direction,
                pens=pens[i:i + 3],
                start_date=pen1.start_date,
                end_date=pen3.end_date,
                start_price=pen1.start_price,
                end_price=pen3.end_price,
                height=round(abs(pen3.end_price - pen1.start_price), 2),
            )
            segments.append(seg)

        i += 1

    return segments


def identify_segments(df: pd.DataFrame) -> pd.DataFrame:
    """完整的线段识别流程"""
    result = df.copy()

    # 1. 先识别笔
    merged = merge_klines(df)
    fractals = find_fractals(merged)
    filtered = filter_fractals(fractals)
    pens = find_pens(filtered)
    segments = find_segments(pens)

    # 2. 标记线段
    result["segment_direction"] = ""
    result["segment_height"] = 0.0

    for seg in segments:
        start_idx = seg.pens[0].start_fractal.k2.idx
        end_idx = seg.pens[-1].end_fractal.k2.idx
        for idx in range(start_idx, end_idx + 1):
            if idx < len(result):
                result.loc[result.index[idx], "segment_direction"] = seg.direction
                result.loc[result.index[idx], "segment_height"] = seg.height

    return result
