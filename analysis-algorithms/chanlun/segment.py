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
    """将笔组合为线段：基于特征序列的线段划分（增强版）

    算法:
      1. 遍历笔序列，以奇数笔方向作为当前线段方向
      2. 特征序列匹配：第1笔和第3笔同向，中间笔反向 → 形成线段
      3. 线段破坏：反向线段出现 → 标记上一线段被破坏
      4. 线段延续：同向连续线段合并
    """
    if not pens or len(pens) < 3:
        return []

    # Step 1: 基本线段识别（特征序列匹配）
    raw_segments = []
    i = 0
    while i <= len(pens) - 3:
        pen1, pen2, pen3 = pens[i], pens[i + 1], pens[i + 2]

        # 特征序列: 奇数笔方向决定线段方向
        if pen1.direction == pen3.direction and \
           pen2.direction != pen1.direction:
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
            raw_segments.append(seg)
        i += 1

    if not raw_segments:
        return []

    # Step 2: 线段破坏标记
    for j in range(1, len(raw_segments)):
        prev = raw_segments[j - 1]
        curr = raw_segments[j]
        if curr.direction != prev.direction:
            prev.destroyed_by = curr.direction
            # 反向线段确认了上一线段的结束

    # Step 3: 线段延续合并（同向段合并）
    merged = []
    current = raw_segments[0]
    for seg in raw_segments[1:]:
        if seg.direction == current.direction:
            # 同向延续：合并
            all_pens = current.pens + seg.pens
            if not current.destroyed_by:
                current = Segment(
                    direction=current.direction,
                    pens=all_pens,
                    start_date=current.start_date,
                    end_date=seg.end_date,
                    start_price=current.start_price,
                    end_price=seg.end_price,
                    height=round(abs(seg.end_price - current.start_price), 2),
                )
            else:
                merged.append(current)
                current = seg
        else:
            merged.append(current)
            current = seg
    merged.append(current)

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

    # 2. 标记线段
    result["segment_direction"] = ""
    result["segment_height"] = 0.0
    result["segment_destroyed"] = ""

    for seg in segments:
        start_idx = seg.pens[0].start_fractal.k2.idx
        end_idx = seg.pens[-1].end_fractal.k2.idx
        for idx in range(start_idx, end_idx + 1):
            if idx < len(result):
                result.loc[result.index[idx], "segment_direction"] = seg.direction
                result.loc[result.index[idx], "segment_height"] = seg.height
                result.loc[result.index[idx], "segment_destroyed"] = seg.destroyed_by or ""

    return result
