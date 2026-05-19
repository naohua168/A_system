"""
缠论图表数据桥接 — 输出前端 ECharts 可渲染的格式

被 Spring Boot 后端以 ProcessBuilder 方式调用:
  python chanlun_bridge.py --code 600519

输出 JSON 格式:
  {
    "bi": [{"x0": 0, "y0": 1320, "x1": 5, "y1": 1380}],
    "zhongshu": [{"startX": 2, "endX": 8, "high": 1458.88, "low": 1452.10}],
    "fengxing": [{"type": "ding", "x": 5, "price": 1380}],
    "stats": {"top_fractals": 7, "bottom_fractals": 7, "pens": 65, "centers": 10},
    "buy_sell_points": [{"type": "buy_1", "date": "2026-01-23", "price": 1325.12}]
  }
"""
import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("chanlun_bridge")


def _load_kline(code: str, days: int = 365) -> pd.DataFrame:
    """从 MySQL 加载 K 线"""
    from data.loader import DataLoader
    dl = DataLoader()
    df = dl.read_kline(code, days)
    dl.close()
    return df


def _run_chanlun_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """执行完整缠论分析并返回前端可渲染格式"""
    from chanlun.fractal import identify_fractals, merge_klines, find_fractals, filter_fractals
    from chanlun.pen import find_pens
    from chanlun.segment import find_segments
    from chanlun.central import find_centrals, identify_centrals
    from chanlun.signal import generate_signals

    # 归一化列名
    work = df.copy()
    if "trade_date" in work.columns and "date" not in work.columns:
        work = work.rename(columns={"trade_date": "date"})

    # 1. 分型 (完整流程)
    merged = merge_klines(work)
    all_fractals = find_fractals(merged)
    filtered = filter_fractals(all_fractals)
    top_count = sum(1 for f in filtered if f.type == "top")
    bottom_count = sum(1 for f in filtered if f.type == "bottom")

    # 构建分型数组 (前端渲染用)
    fengxing = []
    kline_idx_map = {}
    for i, row in work.iterrows():
        kline_idx_map[str(row.get("date", ""))] = i
    for f in filtered:
        x = kline_idx_map.get(str(f.date), 0)
        fengxing.append({
            "type": "ding" if f.type == "top" else "di",
            "x": x,
            "price": f.price,
        })

    # 2. 笔
    pens_obj = find_pens(filtered)
    bi = []
    for pen in pens_obj:
        pen_x0 = kline_idx_map.get(str(pen.start_date), 0)
        pen_x1 = kline_idx_map.get(str(pen.end_date), len(work) - 1)
        bi.append({
            "x0": pen_x0,
            "y0": pen.start_price,
            "x1": pen_x1,
            "y1": pen.end_price,
        })

    # 3. 线段 → 中枢
    segments = find_segments(pens_obj)
    centrals = find_centrals(segments)

    zhongshu = []
    for c in centrals:
        start_x = kline_idx_map.get(str(c.start_date), 0)
        end_x = kline_idx_map.get(str(c.end_date), len(work) - 1)
        zhongshu.append({
            "startX": start_x,
            "endX": end_x,
            "high": c.ZG,
            "low": c.ZD,
        })

    # 4. 买卖信号
    signals = generate_signals(work)
    buy_sell_points = []
    for s in signals:
        buy_sell_points.append({
            "type": s.signal_type,
            "date": s.date,
            "price": s.price,
            "strength": s.strength,
            "description": s.description,
        })

    return {
        "bi": bi,
        "zhongshu": zhongshu,
        "fengxing": fengxing,
        "stats": {
            "top_fractals": top_count,
            "bottom_fractals": bottom_count,
            "pens": len(pens_obj),
            "centers": len(centrals),
            "signals": len(signals),
        },
        "buy_sell_points": buy_sell_points,
    }


def get_chanlun_data(code: str, days: int = 365) -> Dict[str, Any]:
    """获取指定股票的缠论分析数据（供后端/前端调用）"""
    df = _load_kline(code, days)
    if df.empty or len(df) < 30:
        return {"error": f"K线数据不足 (code={code}, rows={len(df)})", "bi": [],
                "zhongshu": [], "fengxing": [], "buy_sell_points": []}

    return _run_chanlun_analysis(df)


def main():
    parser = argparse.ArgumentParser(description="缠论图表数据桥接")
    parser.add_argument("--code", required=True, help="股票代码")
    parser.add_argument("--days", type=int, default=365, help="K线天数")
    args = parser.parse_args()

    try:
        result = get_chanlun_data(args.code, args.days)
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e), "bi": [], "zhongshu": [],
                          "fengxing": [], "buy_sell_points": []},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
