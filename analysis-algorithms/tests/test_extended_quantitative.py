"""量化策略扩展测试"""
import pandas as pd
import numpy as np
import pytest

from quantitative.strategy_base import BaseStrategy, StrategyEngine
from quantitative.ma_strategy import MAStrategy
from quantitative.momentum_strategy import MomentumStrategy
from quantitative.multi_factor_strategy import MultiFactorStrategy
from quantitative.backtest import BacktestEngine, BacktestResult, TradeRecord


class TestStrategyBase:
    def test_abstract(self):
        with pytest.raises(TypeError):
            BaseStrategy()

    def test_get_params_default(self):
        s = MAStrategy()
        assert "fast" in s.get_params()

    def test_get_signals_none(self):
        assert MAStrategy().get_signals() is None


class TestMAStrategy:
    def test_signal_columns(self):
        df = pd.DataFrame({"close": [10 + i*0.3 for i in range(60)], "date": range(60),
                           "high": range(60, 120), "low": range(60), "volume": 1000})
        r = MAStrategy().generate_signals(df)
        assert "signal" in r.columns
        assert r["signal"].isin([-1, 0, 1]).all()

    def test_get_name(self):
        assert "MA" in MAStrategy().get_name()

    def test_params(self):
        s = MAStrategy(fast=10, slow=30)
        assert s.get_params()["fast"] == 10


class TestMomentumStrategy:
    def test_signal_columns(self):
        df = pd.DataFrame({"close": [10 + i*0.5 for i in range(60)], "date": range(60),
                           "volume": 1000})
        r = MomentumStrategy().generate_signals(df)
        assert "signal" in r.columns

    def test_flat_no_signal(self):
        df = pd.DataFrame({"close": [50]*30, "date": range(30), "volume": 1000})
        r = MomentumStrategy(lookback=10, threshold=5.0).generate_signals(df)
        assert (r["signal"] == 0).all()

    def test_get_name(self):
        assert "Momentum" in MomentumStrategy().get_name()


class TestMultiFactor:
    def test_signal_generated(self):
        np.random.seed(42)
        prices = 50 + np.cumsum(np.random.normal(0, 1, 100))
        df = pd.DataFrame({"close": prices, "date": range(100),
                           "high": prices*1.02, "low": prices*0.98,
                           "volume": np.random.randint(500000, 5000000, 100)})
        r = MultiFactorStrategy().generate_signals(df)
        assert "signal" in r.columns

    def test_short_data(self):
        df = pd.DataFrame({"close": [100]*5, "volume": [1000]*5})
        r = MultiFactorStrategy().generate_signals(df)
        assert (r["signal"] == 0).all()

    def test_get_name(self):
        assert "MultiFactor" in MultiFactorStrategy().get_name()


class TestEngine:
    def test_invalid_strategy(self):
        e = StrategyEngine()
        with pytest.raises(TypeError):
            e.add_strategy("bad")

    def test_run_empty(self):
        assert StrategyEngine().run_all(pd.DataFrame()) == []

    def test_run_multiple(self, sample_data):
        e = StrategyEngine()
        e.add_strategy(MAStrategy())
        e.add_strategy(MomentumStrategy())
        r = e.run_all(sample_data)
        assert isinstance(r, list)

    def test_count(self):
        e = StrategyEngine()
        assert e.get_strategy_count() == 0
        e.add_strategy(MAStrategy())
        assert e.get_strategy_count() == 1


class TestBacktest:
    def test_result_dataclass(self):
        r = BacktestResult(10, 8, 15, 1.2, 10, 6, 4, 60.0)
        assert r.total_return_pct == 10

    def test_trade_dataclass(self):
        t = TradeRecord("a", "b", 100, 110, "long", 10, 10)
        assert t.pnl_pct == 10

    def test_no_trades(self, sample_data):
        df = sample_data.copy()
        df["close"] = 100.0
        r = BacktestEngine(100000).run(MAStrategy(), df)
        assert r.total_trades == 0

    def test_with_trades(self, sample_data_trade_date):
        sd = sample_data_trade_date
        df = sd[["close"]].copy()
        df["date"] = sd["trade_date"]
        df["high"] = sd["high"]
        df["low"] = sd["low"]
        df["volume"] = sd["volume"]
        r = BacktestEngine(100000).run(MAStrategy(), df)
        assert isinstance(r, BacktestResult)
