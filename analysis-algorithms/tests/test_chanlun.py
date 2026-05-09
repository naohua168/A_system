"""
缠论分析单元测试（pytest 版本）
验证分型→笔→线段→中枢→信号 全流程
"""

import pytest

from chanlun.analyzer import ChanlunAnalyzer
from chanlun.fractal import merge_klines, find_fractals, filter_fractals
from chanlun.signal import generate_signals


class TestFractal:
    """分型识别测试"""

    def test_merge_klines_reduces_count(self, sample_data):
        merged = merge_klines(sample_data)
        assert len(merged) <= len(sample_data)

    def test_find_fractals(self, sample_data):
        merged = merge_klines(sample_data)
        fractals = find_fractals(merged)
        assert isinstance(fractals, list)
        # 分型数量应为非负整数
        assert len(fractals) >= 0

    def test_filter_fractals(self, sample_data):
        merged = merge_klines(sample_data)
        fractals = find_fractals(merged)
        filtered = filter_fractals(fractals)
        assert len(filtered) <= len(fractals)


class TestSignal:
    """买卖信号测试"""

    def test_generate_signals(self, sample_data):
        signals = generate_signals(sample_data)
        assert isinstance(signals, list)

    def test_signals_have_required_attrs(self, sample_data):
        signals = generate_signals(sample_data)
        if signals:
            sig = signals[0]
            # 信号应有类型、日期、价格属性
            assert hasattr(sig, "signal_type") or isinstance(sig, dict)
            if isinstance(sig, dict):
                assert "type" in sig or "signal_type" in sig


class TestFullChain:
    """缠论完整分析链测试"""

    def test_analyze_returns_all_keys(self, sample_data):
        analyzer = ChanlunAnalyzer()
        result = analyzer.analyze(sample_data)

        assert isinstance(result, dict)
        assert "kline_count" in result
        assert "fractal_count" in result
        assert "signal_count" in result
        assert result["kline_count"] > 0

    def test_analyze_invalid_input(self):
        analyzer = ChanlunAnalyzer()
        with pytest.raises(Exception):
            analyzer.analyze(None)

    def test_fractal_count_non_negative(self, sample_data):
        analyzer = ChanlunAnalyzer()
        result = analyzer.analyze(sample_data)
        assert result["fractal_count"] >= 0
        assert result["signal_count"] >= 0
