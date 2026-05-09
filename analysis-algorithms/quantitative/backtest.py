"""
回测框架
评估策略在历史数据上的表现:
  - 总收益率
  - 年化收益率
  - 最大回撤
  - 夏普比率
  - 交易次数
  - 胜率
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from .strategy_base import BaseStrategy
from .ma_strategy import MAStrategy


@dataclass
class TradeRecord:
    """交易记录"""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    direction: str       # "long" / "short"
    pnl_pct: float       # 收益率
    pnl: float           # 盈亏金额


@dataclass
class BacktestResult:
    """回测结果"""
    total_return_pct: float      # 总收益率
    annual_return_pct: float     # 年化收益率
    max_drawdown_pct: float      # 最大回撤
    sharpe_ratio: float          # 夏普比率
    total_trades: int            # 总交易次数
    win_trades: int              # 盈利次数
    loss_trades: int             # 亏损次数
    win_rate: float              # 胜率
    trades: List[TradeRecord] = field(default_factory=list)


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital

    def run(self, strategy: BaseStrategy, df: pd.DataFrame) -> BacktestResult:
        """运行回测
        Args:
            strategy: 策略实例
            df: K线数据
        Returns:
            回测结果
        """
        signals = strategy.generate_signals(df)

        trades = []
        position = 0  # 0=空仓, 1=持仓
        entry_price = 0.0
        entry_date = ""
        capital = self.initial_capital
        equity_curve = [capital]

        # 逐日模拟
        for i, (_, row) in enumerate(signals.iterrows()):
            if pd.isna(row.get("close")):
                equity_curve.append(capital)
                continue

            price = float(row["close"])
            signal = int(row.get("signal", 0))

            # 买入信号且空仓
            if signal == 1 and position == 0:
                position = 1
                entry_price = price
                entry_date = str(row["date"])

            # 卖出信号且持仓
            elif signal == -1 and position == 1:
                pnl_pct = (price - entry_price) / entry_price * 100
                pnl = capital * pnl_pct / 100
                capital += pnl

                trades.append(TradeRecord(
                    entry_date=entry_date,
                    exit_date=str(row["date"]),
                    entry_price=round(entry_price, 2),
                    exit_price=round(price, 2),
                    direction="long",
                    pnl_pct=round(pnl_pct, 2),
                    pnl=round(pnl, 2),
                ))
                position = 0
                entry_price = 0.0

            equity_curve.append(capital)

        # 计算绩效指标
        equity_series = pd.Series(equity_curve)
        total_return = (capital - self.initial_capital) / self.initial_capital * 100

        # 年化收益
        years = len(df) / 252  # 假设252个交易日/年
        annual_return = (math.pow(1 + total_return / 100, 1 / years) - 1) * 100 if years > 0 else 0.0

        # 最大回撤
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak * 100
        max_drawdown = abs(drawdown.min())

        # 夏普比率
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe = math.sqrt(252) * daily_returns.mean() / daily_returns.std()
        else:
            sharpe = 0.0

        # 胜率
        win_trades = sum(1 for t in trades if t.pnl_pct > 0)
        loss_trades = sum(1 for t in trades if t.pnl_pct <= 0)
        win_rate = win_trades / len(trades) * 100 if trades else 0.0

        return BacktestResult(
            total_return_pct=round(total_return, 2),
            annual_return_pct=round(annual_return, 2),
            max_drawdown_pct=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe, 2),
            total_trades=len(trades),
            win_trades=win_trades,
            loss_trades=loss_trades,
            win_rate=round(win_rate, 2),
            trades=trades,
        )


def main():
    """回测 CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="量化回测引擎")
    parser.add_argument("--file", help="CSV 数据文件")
    parser.add_argument("--fast", type=int, default=5, help="短周期")
    parser.add_argument("--slow", type=int, default=20, help="长周期")
    parser.add_argument("--capital", type=float, default=100000, help="初始资金")
    args = parser.parse_args()

    if args.file:
        df = pd.read_csv(args.file)
    else:
        # 使用示例数据
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
        from utils.data_loader import load_sample
        df = load_sample()
        print("⚠️  使用示例数据，共", len(df), "条")

    strategy = MAStrategy(fast=args.fast, slow=args.slow)
    engine = BacktestEngine(initial_capital=args.capital)
    result = engine.run(strategy, df)

    print(f"\n📊 回测结果: {strategy.get_name()}")
    print(f"{'='*50}")
    print(f"  初始资金:    {engine.initial_capital:>10,.0f}")
    print(f"  最终资金:    {engine.initial_capital * (1 + result.total_return_pct / 100):>10,.0f}")
    print(f"  总收益率:    {result.total_return_pct:>10.2f}%")
    print(f"  年化收益率:  {result.annual_return_pct:>10.2f}%")
    print(f"  最大回撤:    {result.max_drawdown_pct:>10.2f}%")
    print(f"  夏普比率:    {result.sharpe_ratio:>10.2f}")
    print(f"  交易次数:    {result.total_trades:>10}")
    print(f"  胜率:        {result.win_rate:>10.2f}%")


if __name__ == "__main__":
    main()
