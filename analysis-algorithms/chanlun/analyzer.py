"""
缠论 — 统一分析入口
一键完成: K线包含处理 → 分型 → 笔 → 线段 → 中枢 → 信号
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from .fractal import identify_fractals
from .pen import identify_pens
from .segment import identify_segments
from .central import identify_centrals
from .signal import generate_signals
from .visualizer import ChanlunVisualizer


class ChanlunAnalyzer:
    """缠论分析器 — 统一入口"""

    def __init__(self):
        self.result_df: Optional[pd.DataFrame] = None
        self.signals = []

    def analyze(self, df: pd.DataFrame) -> dict:
        """执行完整缠论分析
        Args:
            df: K线数据，需包含 date, open, high, low, close, volume
        Returns:
            分析结果 dict (同 visualizer.to_dict 格式)
        """
        if df.empty:
            return {"error": "无数据"}

        print(f"📊 缠论分析: {len(df)} 条K线")

        # 1. 分型
        df = identify_fractals(df)
        top_count = len(df[df["fractal_type"] == "top"])
        bottom_count = len(df[df["fractal_type"] == "bottom"])
        print(f"   ✅ 分型: {top_count} 顶 + {bottom_count} 底")

        # 2. 笔
        df = identify_pens(df)
        pen_count = len(df[df["pen_direction"] != ""])
        print(f"   ✅ 笔识别完成")

        # 3. 线段
        df = identify_segments(df)
        print(f"   ✅ 线段识别完成")

        # 4. 中枢
        df = identify_centrals(df)
        central_count = len(df[df["central_ZG"] > 0])
        print(f"   ✅ 中枢: {central_count}条K线在中枢区间内")

        # 5. 买卖信号
        signals = generate_signals(df)
        print(f"   ✅ 信号: {len(signals)} 个")
        for s in signals:
            print(f"      {s.signal_type}: {s.date} @ {s.price}")

        self.result_df = df
        self.signals = signals

        return ChanlunVisualizer.to_dict(df)

    def analyze_from_csv(self, filepath: str) -> dict:
        """从 CSV 文件加载数据并分析"""
        df = pd.read_csv(filepath)
        return self.analyze(df)

    def get_signals_summary(self) -> str:
        """获取买卖信号文字摘要"""
        if not self.signals:
            return "⚠️  未检测到买卖信号"

        lines = ["📈 缠论买卖信号摘要:"]
        for s in self.signals:
            lines.append(f"   {s.signal_type}: {s.date} 价格={s.price} 强度={s.strength}%")
            lines.append(f"       {s.description}")
        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="缠论分析器")
    parser.add_argument("file", nargs="?", help="CSV 数据文件路径")
    parser.add_argument("--code", default="000001", help="股票代码（不传文件时自动采集）")
    parser.add_argument("--days", type=int, default=365, help="采集天数")
    args = parser.parse_args()

    analyzer = ChanlunAnalyzer()

    if args.file:
        df = pd.read_csv(args.file)
    else:
        # 从 MySQL 或生成示例数据
        try:
            from data.loader import DataLoader
            dl = DataLoader()
            df = dl.read_kline(args.code, days=args.days)
            dl.close()
        except Exception:
            import numpy as np
            np.random.seed(42)
            n = 120
            dates = pd.bdate_range("2025-01-01", periods=n)
            base, trend = 10.0, np.linspace(0, 2, n)
            noise = np.random.normal(0, 0.2, n).cumsum()
            closes = base + trend + noise
            df = pd.DataFrame({
                "date": dates.strftime("%Y-%m-%d"),
                "open": closes - np.random.uniform(0, 0.3, n),
                "high": closes + np.random.uniform(0, 0.5, n),
                "low": closes - np.random.uniform(0, 0.5, n),
                "close": closes,
                "volume": np.random.randint(500000, 5000000, n),
            })
            print("⚠️  使用模拟数据")

    if df.empty:
        print("❌ 无数据")
        return

    result = analyzer.analyze(df)
    print("\n" + analyzer.get_signals_summary())


if __name__ == "__main__":
    main()
