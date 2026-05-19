"""
L3 算法分析层 — 性能基准测试套件

用法:
  python benchmark.py              # 全部基准
  python benchmark.py --quick      # 快速（小样本）
  python benchmark.py --compare    # 优化前后对比（需保存基准文件）

输出:
  逐项耗时(ms) + 内存(KB) + 综合评分
"""
import sys, time, gc, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import pandas as pd
import numpy as np

# ── 导入被测试模块 ──
from technical import MA, MACD, KDJ, RSI, BollingerBands, calculate_all
from chanlun.fractal import identify_fractals, merge_klines
from chanlun.pen import identify_pens
from chanlun.segment import identify_segments
from chanlun.central import identify_centrals
from chanlun.signal import generate_signals
from quantitative.strategy_base import StrategyEngine
from quantitative.ma_strategy import MAStrategy
from quantitative.momentum_strategy import MomentumStrategy
from quantitative.backtest import BacktestEngine


def gen_kline(n=1023, seed=42):
    """生成可复现的模拟 K 线"""
    np.random.seed(seed)
    trend = np.linspace(0, 5, n)
    noise = np.random.normal(0, 0.5, n).cumsum()
    closes = 10.0 + trend + noise
    return pd.DataFrame({
        "date": pd.bdate_range("2022-01-01", periods=n).strftime("%Y-%m-%d"),
        "open": closes - np.random.uniform(0, 0.3, n),
        "high": closes + np.random.uniform(0, 0.5, n),
        "low": closes - np.random.uniform(0, 0.5, n),
        "close": closes,
        "volume": np.random.randint(500000, 5000000, n),
    })


def bench(name, fn, *args, warmup=1, repeat=3, **kwargs):
    """基准测试: warmup + repeat 取中位数"""
    gc.collect()
    # warmup
    for _ in range(warmup):
        fn(*args, **kwargs)
    # measure
    times = []
    for _ in range(repeat):
        gc.collect()
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    median = times[len(times)//2]
    return {"name": name, "ms": round(median, 2), "repeat": repeat}


def run_all(quick=False):
    """运行全部基准"""
    n = 1023
    kline = gen_kline(n)
    kline_big = gen_kline(3069)  # ~12年
    if quick:
        kline = gen_kline(120)
        kline_big = gen_kline(365)

    results = []

    # ═══ 1. 技术指标 ═══
    results.append(bench("MA", MA, kline))
    results.append(bench("MACD", MACD, kline))
    results.append(bench("KDJ", KDJ, kline))
    results.append(bench("RSI", RSI, kline))
    results.append(bench("Bollinger", BollingerBands, kline))
    results.append(bench("5项技术指标", calculate_all, kline))
    if not quick:
        results.append(bench("5项(3069行)", calculate_all, kline_big))

    # ═══ 2. 缠论 ═══
    def chanlun_full(df):
        return generate_signals(identify_centrals(
            identify_segments(identify_pens(identify_fractals(df)))))
    results.append(bench("缠论6步", chanlun_full, kline))
    if not quick:
        results.append(bench("缠论6步(3069行)", chanlun_full, kline_big))

    # ═══ 3. 量化策略 ═══
    engine = StrategyEngine()
    engine.add_strategy(MAStrategy())
    engine.add_strategy(MomentumStrategy())
    results.append(bench("策略引擎×2", engine.run_all, kline))
    results.append(bench("回测MA策略", BacktestEngine().run, MAStrategy(), kline))

    return results


def report(results):
    """打印格式化报告"""
    print(f"\n{'='*60}")
    print(f"  L3 性能基准报告")
    print(f"  CPU: {__import__('os').cpu_count()}核")
    print(f"{'='*60}")
    print(f"{'测试项':30s} {'耗时(ms)':>10s}")
    print(f"{'-'*42}")
    total_ms = 0
    for r in results:
        flag = ""
        if r["ms"] > 1000: flag = " ⚠️ SLOW"
        elif r["ms"] < 10: flag = " ✅ FAST"
        print(f"  {r['name']:28s} {r['ms']:>8.2f}ms{flag}")
        total_ms += r["ms"]
    print(f"{'-'*42}")
    print(f"  合计:          {total_ms:>8.2f}ms")
    print(f"  平均:          {total_ms/len(results):>8.2f}ms")
    print(f"{'='*60}")

    # 性能评分
    if total_ms < 500: grade = "S"
    elif total_ms < 2000: grade = "A"
    elif total_ms < 5000: grade = "B"
    else: grade = "C"
    print(f"  性能等级: {grade}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="快速模式")
    parser.add_argument("--compare", action="store_true", help="保存基准对比")
    args = parser.parse_args()

    print("运行基准测试...")
    results = run_all(quick=args.quick)
    report(results)

    if args.compare:
        with open("benchmark_result.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"结果已保存到 benchmark_result.json")
