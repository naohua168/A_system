"""
缠论 — 笔识别

笔 = 相邻顶底分型的连接
规则:
  1. 顶分型和底分型交替出现
  2. 顶和底之间至少间隔 1 根K线（不含分型本身）
  3. 上升笔 = 底 → 顶
  4. 下降笔 = 顶 → 底
"""

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from .fractal import Fractal, filter_fractals, find_fractals, merge_klines, identify_fractals


@dataclass
class Pen:
    """笔"""
    direction: str        # "up" 上升笔 / "down" 下降笔
    start_fractal: Fractal  # 起始分型
    end_fractal: Fractal    # 终止分型
    start_price: float      # 起始价
    end_price: float        # 终止价
    start_date: str         # 起始日期
    end_date: str           # 终止日期
    height: float = 0.0     # 笔的高度

    @property
    def change_pct(self) -> float:
        if self.start_price > 0:
            return round((self.end_price - self.start_price) / self.start_price * 100, 2)
        return 0.0


def find_pens(fractals: Optional[List[Fractal]]) -> List[Pen]:
    """连接分型为笔
    Args:
        fractals: 已过滤的分型列表
    Returns:
        笔列表
    """
    if not fractals or len(fractals) < 2:
        return []

    pens = []
    for i in range(len(fractals) - 1):
        start = fractals[i]
        end = fractals[i + 1]

        if start.type == "bottom" and end.type == "top":
            direction = "up"
            start_price = start.price
            end_price = end.price
        elif start.type == "top" and end.type == "bottom":
            direction = "down"
            start_price = start.price
            end_price = end.price
        else:
            # 相同类型，跳过
            continue

        pen = Pen(
            direction=direction,
            start_fractal=start,
            end_fractal=end,
            start_price=start_price,
            end_price=end_price,
            start_date=start.date,
            end_date=end.date,
            height=round(abs(end_price - start_price), 2),
        )
        pens.append(pen)

    return pens


def identify_pens(df: pd.DataFrame) -> pd.DataFrame:
    """完整笔识别流程: 包含处理 → 分型 → 笔
    Args:
        df: K线数据
    Returns:
        带分型和笔标记的 DataFrame
    """
    # 1. 先得分型
    result = identify_fractals(df)

    # 2. 获取分型列表
    merged = merge_klines(df)
    all_fractals = find_fractals(merged)
    filtered = filter_fractals(all_fractals)
    pens = find_pens(filtered)

    # 3. 标记笔 — 向量化切片赋值替代逐行循环
    result["pen_direction"] = ""
    result["pen_height"] = 0.0
    result["pen_change_pct"] = 0.0

    for pen in pens:
        start_idx = pen.start_fractal.k2.idx
        end_idx = pen.end_fractal.k2.idx

        if start_idx < len(result) and end_idx < len(result):
            # 批量赋值：用切片替代 range 循环
            idx_slice = result.index[start_idx:end_idx + 1]
            n = len(idx_slice)
            result.loc[idx_slice, "pen_direction"] = [pen.direction] * n
            result.loc[idx_slice, "pen_height"] = [pen.height] * n
            result.loc[idx_slice, "pen_change_pct"] = [pen.change_pct] * n

    return result
