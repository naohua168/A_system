"""
缠论 — 可视化接口
将缠论分析结果序列化为 JSON，供后端 API 调用和前端展示
"""

import json
from typing import List

import pandas as pd

from .fractal import identify_fractals
from .pen import identify_pens
from .segment import identify_segments
from .central import identify_centrals
from .signal import generate_signals, TradeSignal


class ChanlunVisualizer:
    """缠论结果转 JSON/字典"""

    @staticmethod
    def to_dict(df: pd.DataFrame) -> dict:
        """将缠论分析结果转为字典"""
        result = identify_fractals(df)
        result = identify_pens(result)
        result = identify_segments(result)
        result = identify_centrals(result)
        signals = generate_signals(df)

        # K线数据
        kline_data = []
        for _, row in result.iterrows():
            kline_data.append({
                "date": str(row.get("date", "")),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": int(row.get("volume", 0)),
                "fractal_type": str(row.get("fractal_type", "")),
                "fractal_price": float(row.get("fractal_price", 0)),
                "pen_direction": str(row.get("pen_direction", "")),
                "pen_height": float(row.get("pen_height", 0)),
                "segment_direction": str(row.get("segment_direction", "")),
                "central_ZG": float(row.get("central_ZG", 0)),
                "central_ZD": float(row.get("central_ZD", 0)),
            })

        # 分型点
        fractals = []
        for _, row in result.iterrows():
            ftype = str(row.get("fractal_type", ""))
            if ftype:
                fractals.append({
                    "type": ftype,
                    "date": str(row["date"]),
                    "price": float(row["fractal_price"]),
                    "strength": float(row.get("fractal_strength", 0)),
                })

        # 中枢
        centrals = []
        valid = result[result["central_ZG"] > 0]
        if not valid.empty:
            last = valid.iloc[-1]
            centrals.append({
                "ZG": float(last["central_ZG"]),
                "ZD": float(last["central_ZD"]),
                "ZF": float(last["central_ZF"]),
                "mid": float(last["central_mid"]),
            })

        # 信号
        signal_list = [
            {
                "type": s.signal_type,
                "date": s.date,
                "price": s.price,
                "strength": s.strength,
                "description": s.description,
            }
            for s in signals
        ]

        return {
            "stock_code": "",
            "kline_count": len(kline_data),
            "fractal_count": len(fractals),
            "central_count": len(centrals),
            "signal_count": len(signal_list),
            "kline_data": kline_data[-120:] if len(kline_data) > 120 else kline_data,
            "fractals": fractals,
            "centrals": centrals,
            "signals": signal_list,
        }

    @staticmethod
    def to_json(df: pd.DataFrame, indent: int = 2) -> str:
        """将缠论分析结果转为 JSON 字符串"""
        return json.dumps(ChanlunVisualizer.to_dict(df), ensure_ascii=False, indent=indent)
