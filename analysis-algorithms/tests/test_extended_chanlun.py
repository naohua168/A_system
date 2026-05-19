"""缠论扩展测试 — 边界条件全覆盖"""
import pandas as pd
import numpy as np
import pytest

from chanlun.fractal import (
    KLine, Fractal, merge_klines, find_fractals, filter_fractals,
    identify_fractals, _calc_strength,
)
from chanlun.pen import find_pens, identify_pens
from chanlun.segment import find_segments, identify_segments
from chanlun.central import find_centrals, identify_centrals
from chanlun.signal import TradeSignal, generate_signals, _get_active_central
from chanlun.analyzer import ChanlunAnalyzer
from chanlun.visualizer import ChanlunVisualizer


class TestFractalEdgeCases:
    def test_kline_mid(self):
        k = KLine("d", 10, 5)
        assert k.mid == 7.5

    def test_merge_empty(self):
        assert merge_klines(pd.DataFrame()) == []

    def test_merge_single(self, small_sample):
        r = merge_klines(small_sample.iloc[:1])
        assert len(r) == 1

    def test_no_overlap(self):
        df = pd.DataFrame({"date": ["a", "b", "c"],
                           "high": [10, 12, 11], "low": [8, 9, 7]})
        assert len(merge_klines(df)) == 3

    def test_strength_top(self):
        k1, k2, k3 = KLine("a", 10, 8), KLine("b", 15, 11), KLine("c", 9, 7)
        assert _calc_strength(k1, k2, k3, "top") == (5 + 6)

    def test_strength_bottom(self):
        k1, k2, k3 = KLine("a", 10, 8), KLine("b", 9, 5), KLine("c", 11, 7)
        assert _calc_strength(k1, k2, k3, "bottom") == (3 + 2)

    def test_find_fractals_short(self):
        assert find_fractals([]) == []
        assert find_fractals([KLine("a", 1, 0), KLine("b", 2, 1)]) == []

    def test_filter_empty(self):
        assert filter_fractals([]) == []

    def test_identify_empty(self):
        r = identify_fractals(pd.DataFrame({"high": [], "low": [], "close": []}))
        assert "fractal_type" in r.columns

    def test_trade_date_col(self):
        df = pd.DataFrame({"trade_date": ["a", "b", "c"],
                           "high": [10, 15, 11], "low": [8, 12, 9],
                           "close": [9, 13, 10]})
        r = identify_fractals(df)
        assert "fractal_type" in r.columns


class TestPenEdgeCases:
    def test_find_empty(self):
        assert find_pens(None) == []
        assert find_pens([]) == []

    def test_identify_empty(self):
        assert identify_pens(pd.DataFrame()).empty

    def test_full_cycle(self, sample_data):
        r = identify_pens(sample_data)
        assert "pen_direction" in r.columns


class TestSegmentEdgeCases:
    def test_find_empty(self):
        assert find_segments(None) == []
        assert find_segments([]) == []

    def test_identify_empty(self):
        assert identify_segments(pd.DataFrame()).empty

    def test_full_cycle(self, sample_data):
        df = identify_fractals(sample_data)
        df = identify_pens(df)
        r = identify_segments(df)
        assert "segment_direction" in r.columns


class TestCentralEdgeCases:
    def test_find_empty(self):
        assert find_centrals([]) == []

    def test_identify_empty(self):
        assert identify_centrals(pd.DataFrame()).empty

    def test_full_cycle(self, sample_data):
        r = identify_centrals(sample_data)
        assert "central_ZG" in r.columns


class TestSignal:
    def test_get_active_empty(self):
        zg, zd = _get_active_central(pd.DataFrame({"central_ZG": [], "central_ZD": [],
                                                     "date": []}), "2025-01-01")
        assert zg == 0 and zd == 0

    def test_get_active_with_data(self):
        df = pd.DataFrame({"central_ZG": [15.0], "central_ZD": [10.0], "date": ["2025-01-05"]})
        zg, zd = _get_active_central(df, "2025-01-10")
        assert zg == 15.0 and zd == 10.0

    def test_generate_empty(self):
        assert generate_signals(pd.DataFrame()) == []

    def test_trade_signal_repr(self):
        s = TradeSignal("buy_1", "2025-01-01", 100.0)
        assert "buy" in str(s)


class TestVisualizer:
    def test_to_dict_with_data(self, sample_data):
        r = ChanlunVisualizer.to_dict(sample_data)
        assert isinstance(r, dict)

    def test_to_dict_empty(self):
        r = ChanlunVisualizer.to_dict(pd.DataFrame())
        assert isinstance(r, dict)

    def test_to_json(self, sample_data):
        j = ChanlunVisualizer.to_json(sample_data)
        assert isinstance(j, str) and len(j) > 10


class TestAnalyzer:
    def test_analyze_empty(self):
        r = ChanlunAnalyzer().analyze(pd.DataFrame())
        assert "error" in r

    def test_analyze_with_data(self, sample_data):
        r = ChanlunAnalyzer().analyze(sample_data)
        assert isinstance(r, dict)

    def test_summary_empty(self):
        s = ChanlunAnalyzer().get_signals_summary()
        assert "未检测到" in s

    def test_summary_with_data(self, sample_data):
        a = ChanlunAnalyzer()
        a.analyze(sample_data)
        s = a.get_signals_summary()
        assert isinstance(s, str)
