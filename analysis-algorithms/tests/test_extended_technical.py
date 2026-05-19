"""技术指标扩展测试 — 信号函数 + 边界条件"""
import pandas as pd
import numpy as np
import pytest
from technical import MA, ma_cross_signal, MACD, macd_signal, KDJ, RSI, rsi_signal
from technical import BollingerBands, bollinger_signal, calculate_all


class TestMACrossSignal:
    def test_columns(self, sample_data):
        df = ma_cross_signal(sample_data)
        for c in ("MA_fast", "MA_slow", "signal", "cross", "cross_signal"):
            assert c in df.columns

    def test_trend_detection(self):
        n = 60
        close = [10 + i * 0.3 for i in range(n)]
        df = pd.DataFrame({"close": close})
        r = ma_cross_signal(df, fast=5, slow=20)
        assert "cross_signal" in r.columns


class TestMACDSignal:
    def test_columns(self, sample_data):
        df = MACD(sample_data)
        r = macd_signal(df)
        for c in ("dif_above_dea", "macd_cross", "macd_signal_str"):
            assert c in r.columns

    def test_with_data(self):
        n = 60
        close = [10 + i**1.5 / 3 for i in range(n)]
        df = MACD(pd.DataFrame({"close": close}))
        r = macd_signal(df)
        assert "macd_signal_str" in r.columns


class TestRSISignal:
    def test_columns(self, sample_data):
        df = RSI(sample_data)
        r = rsi_signal(df, period=6)
        for c in ("rsi_overbought", "rsi_oversold"):
            assert c in r.columns

    def test_empty(self):
        df = pd.DataFrame({"RSI14": []})
        r = rsi_signal(df, period=14)
        assert "rsi_overbought" in r.columns or r.empty


class TestBollingerSignal:
    def test_columns(self):
        n = 30
        close = [50 + i * 1.5 for i in range(n)]
        df = BollingerBands(pd.DataFrame({"close": close}))
        r = bollinger_signal(df)
        for c in ("boll_upper_touch", "boll_lower_touch"):
            assert c in r.columns


class TestEdgeCases:
    def test_ma_single_row(self):
        df = MA(pd.DataFrame({"close": [100.0]}))
        assert "MA5" in df.columns

    def test_kdj_no_variance(self):
        df = KDJ(pd.DataFrame({"high": [10, 10, 10], "low": [10, 10, 10],
                                "close": [10, 10, 10]}))
        assert "K" in df.columns

    def test_calculate_all_empty(self):
        with pytest.raises(Exception):
            calculate_all(pd.DataFrame())
