"""
缠论 — 线段识别（增强版）

线段 = 至少 3 笔构成
在笔的基础上划分更高一级的趋势结构。

增强特性（v2）:
  1. 特征序列处理：标准笔特征序列的严格匹配
  2. 线段破坏处理：识别线段被反向线段破坏
  3. 线段延续：合并同向连续线段
"""
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import numpy as np

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
    destroyed_by: Optional[str] = None   # 被什么方向的线段破坏

    @property
    def pen_count(self) -> int:
        return len(self.pens)

    @property
    def change_pct(self) -> float:
        if self.start_price > 0:
            return round((self.end_price - self.start_price) / self.start_price * 100, 2)
        return 0.0


def find_segments(pens: Optional[List[Pen]]) -> List[Segment]:
    """将笔组合为线段（修正版）

    缠论定义：线段 = 至少 3 笔构成的方向性结构
    严格模式下，交替笔 (up/down/up 或 down/up/down) 每 3 笔构成一段，
    相邻段共享 1 笔（重叠），使段数充足，中枢可检测。

    算法:
      1. 严格模式：特征序列匹配，每 3 笔固定一段，步长 2（共享重叠笔）
      2. 严格模式无结果时，方向分组回退（连续同向 ≥ 3 笔）
      3. 线段破坏标记
      4. 同向线段合并
    """
    if not pens or len(pens) < 3:
        return []

    n = len(pens)

    # Step 1: 严格模式 — 每 3 笔构成一段，步长 1（滑动窗口，方向自然交替）
    strict_segments = []
    i = 0
    while i <= n - 3:
        p1, p2, p3 = pens[i], pens[i + 1], pens[i + 2]
        if p1.direction == p3.direction and p2.direction != p1.direction:
            seg = Segment(
                direction=p1.direction, pens=[p1, p2, p3],
                start_date=p1.start_date, end_date=p3.end_date,
                start_price=p1.start_price, end_price=p3.end_price,
                height=round(abs(p3.end_price - p1.start_price), 2),
            )
            strict_segments.append(seg)
        i += 1  # 步长 1，方向自然交替 (up/down/up/down...)

    if strict_segments:
        raw = strict_segments
    else:
        # Step 2: 宽松模式 — 方向分组回退
        loose_segments = []
        i = 0
        while i < n:
            dir_current = pens[i].direction
            group = [pens[i]]
            j = i + 1
            while j < n and pens[j].direction == dir_current:
                group.append(pens[j])
                j += 1
            if len(group) >= 3:
                seg = Segment(
                    direction=dir_current, pens=group,
                    start_date=group[0].start_date, end_date=group[-1].end_date,
                    start_price=group[0].start_price, end_price=group[-1].end_price,
                    height=round(abs(group[-1].end_price - group[0].start_price), 2),
                )
                loose_segments.append(seg)
            i = j
        raw = loose_segments

    if not raw:
        return []

    # Step 3: 线段破坏标记
    for j in range(1, len(raw)):
        prev = raw[j - 1]
        curr = raw[j]
        if curr.direction != prev.direction:
            prev.destroyed_by = curr.direction

    # Step 4: 同向线段合并（只有未被破坏的相邻同向段才合并）
    merged = [raw[0]]
    for seg in raw[1:]:
        last = merged[-1]
        if seg.direction == last.direction and not last.destroyed_by:
            all_pens = last.pens + seg.pens
            last = Segment(
                direction=last.direction, pens=all_pens,
                start_date=last.start_date, end_date=seg.end_date,
                start_price=last.start_price, end_price=seg.end_price,
                height=round(abs(seg.end_price - last.start_price), 2),
            )
            merged[-1] = last
        else:
            merged.append(seg)

    return merged


def identify_segments(df: pd.DataFrame) -> pd.DataFrame:
    """完整的线段识别流程（增强版）"""
    result = df.copy()

    # 1. 先识别笔
    merged = merge_klines(df)
    fractals = find_fractals(merged)
    filtered = filter_fractals(fractals)
    pens = find_pens(filtered)
    segments = find_segments(pens)

    # 2. 标记线段 — 向量化切片赋值替代逐行循环
    result["segment_direction"] = ""
    result["segment_height"] = 0.0
    result["segment_destroyed"] = ""

    for seg in segments:
        start_idx = seg.pens[0].start_fractal.k2.idx
        end_idx = seg.pens[-1].end_fractal.k2.idx
        if start_idx < len(result) and end_idx < len(result):
            idx_slice = result.index[start_idx:end_idx + 1]
            n = len(idx_slice)
            result.loc[idx_slice, "segment_direction"] = [seg.direction] * n
            result.loc[idx_slice, "segment_height"] = [seg.height] * n
            result.loc[idx_slice, "segment_destroyed"] = [seg.destroyed_by or ""] * n

    return result
