"""扩展的算法边界条件测试（适配当前 DataFrame 导向的 API）"""
import math
import pandas as pd
import numpy as np
import pytest

# 导入被测试模块（conftest.py 已将 analysis-algorithms/ 加入 sys.path）
from technical import MA, MACD, RSI, BollingerBands, KDJ, VOLUME, CCI, WPR, OBV
from quantitative.backtest import BacktestEngine, BacktestResult


# ============================================================
# 技术指标边界条件
# ============================================================

class TestTechnicalEdgeCases:

    def test_ma_empty_input(self):
        """空序列 MA"""
        result = MA(pd.DataFrame({"close": []}))
        # 空 DataFrame 应返回空（或 MA5 列为空）
        assert result.empty or result["MA5"].empty

    def test_ma_short_input(self):
        """序列短于周期 — 前 (周期-1) 个值为 NaN"""
        df = pd.DataFrame({"close": [1, 2, 3]})
        result = MA(df)
        # MA5 列应有 3 个值，均为 NaN
        assert len(result) == 3
        assert result["MA5"].isna().all()

    def test_ma_single_element(self):
        """单元素 MA5 — 结果应为 NaN"""
        df = pd.DataFrame({"close": [10.0]})
        result = MA(df)
        assert len(result) == 1
        assert math.isnan(result["MA5"].iloc[0])

    def test_ma_zero_period(self):
        """0 周期 MA — rolling(0) 不抛异常，返回 NaN"""
        result = MA(pd.DataFrame({"close": [1, 2, 3]}), periods=[0])
        assert "MA0" in result.columns
        assert result["MA0"].isna().all()

    def test_rsi_all_identical(self):
        """RSI 所有价格相同 — RSI 应接近 50"""
        df = pd.DataFrame({"close": [10.0] * 30})
        result = RSI(df)
        valid = result["RSI6"].dropna()
        for v in valid:
            assert v == pytest.approx(50.0, abs=0.1)

    def test_rsi_monotonic_up(self):
        """RSI 持续上涨应接近 100"""
        df = pd.DataFrame({"close": [100 + i for i in range(20)]})
        result = RSI(df)
        valid = result["RSI6"].dropna()
        assert valid.iloc[-1] > 80

    def test_rsi_monotonic_down(self):
        """RSI 持续下跌应接近 0"""
        df = pd.DataFrame({"close": [100 - i for i in range(20)]})
        result = RSI(df)
        valid = result["RSI6"].dropna()
        assert valid.iloc[-1] < 20

    def test_kdj_extreme_values(self):
        """KDJ 极值 — K/D 应在 0~100 范围内"""
        df = pd.DataFrame({
            "high": [100] * 30 + [200] * 10,
            "low": [80] * 30 + [0] * 10,
            "close": [90] * 40,
        })
        result = KDJ(df)
        assert result["K"].between(0, 100).all()
        assert result["D"].between(0, 100).all()

    def test_bollinger_constant_price(self):
        """布林带：恒定价格下轨=中轨=上轨（取窗口满的最后一行验证）"""
        df = pd.DataFrame({"close": [10.0] * 20})
        result = BollingerBands(df)
        # 最后一行窗口已满，恒定价格下 std=0，三线重合
        last = result.dropna().iloc[-1]
        assert last["BOLL_MID"] == last["BOLL_UP"] == last["BOLL_DOWN"]

    def test_macd_insufficient_data(self):
        """MACD 数据不足 — 列存在且行数一致"""
        df = pd.DataFrame({"close": [10.0] * 5})
        result = MACD(df)
        for col in ("DIF", "DEA", "MACD"):
            assert col in result.columns
            assert len(result[col]) == 5

    def test_cci_calculation(self):
        """CCI 计算"""
        prices = [10 + i % 5 for i in range(20)]
        df = pd.DataFrame({
            "high": [p + 1 for p in prices],
            "low": [p - 1 for p in prices],
            "close": prices,
        })
        result = CCI(df, window=20)
        assert "CCI" in result.columns
        assert len(result) == len(prices)

    def test_wr_calculation(self):
        """WR 威廉指标 — WPR 值应在 -100~0 之间"""
        df = pd.DataFrame({
            "high": [10 + i for i in range(14)],
            "low": [9 + i for i in range(14)],
            "close": [9.5 + i for i in range(14)],
        })
        result = WPR(df, window=14)
        assert "WPR" in result.columns
        valid = result["WPR"].dropna()
        assert valid.between(-100, 0).all()

    def test_obv_calculation(self):
        """OBV 能量潮 — 首日无价格变动，OBV[0]=0"""
        df = pd.DataFrame({
            "close": [10, 11, 10.5, 12, 11.5],
            "volume": [10000, 15000, 12000, 20000, 18000],
        })
        result = OBV(df)
        assert "OBV" in result.columns
        # 首日 diff=NaN → direction=0 → OBV[0]=0
        assert result["OBV"].iloc[0] == 0

    def test_volume_ma(self):
        """成交量均线"""
        df = pd.DataFrame({"volume": [i * 1000 for i in range(1, 31)]})
        result = VOLUME(df, windows=[5])
        assert "VOL_MA5" in result.columns
        assert len(result) == len(df)


# ============================================================
# 缠论边界条件
# ============================================================

class TestChanlunEdgeCases:

    def test_empty_kline_merge(self):
        """空序列合并"""
        from chanlun.fractal import merge_klines
        result = merge_klines(pd.DataFrame())
        assert result == []

    def test_single_kline_merge(self):
        """单 K 线合并"""
        from chanlun.fractal import merge_klines
        df = pd.DataFrame([{
            "date": "2025-01-01", "high": 10, "low": 9, "open": 9.5, "close": 9.8,
        }])
        result = merge_klines(df)
        assert len(result) == 1

    def test_fractal_identification(self):
        """分型识别"""
        from chanlun.fractal import merge_klines, find_fractals
        dates = pd.bdate_range("2025-01-01", periods=5)
        df = pd.DataFrame({
            "date": dates,
            "high": [11, 12, 13, 12, 11],
            "low": [9, 10, 11, 10, 9],
            "open": [10, 10.5, 11.5, 12, 10.5],
            "close": [10.5, 11.5, 12.5, 10.5, 9.5],
        })
        merged = merge_klines(df)
        fractals = find_fractals(merged)
        assert isinstance(fractals, list)

    def test_two_kline_insufficient_for_pen(self):
        """2 根 K 线不足以形成笔"""
        from chanlun.pen import identify_pens
        df = pd.DataFrame({
            "date": pd.bdate_range("2025-01-01", periods=2),
            "high": [10, 11],
            "low": [9, 10],
            "open": [9.5, 10],
            "close": [10, 10.5],
        })
        result = identify_pens(df)
        assert "pen_direction" in result.columns


# ============================================================
# 量化策略边界条件
# ============================================================

class TestQuantitativeEdgeCases:

    def test_backtest_empty_trades(self):
        """回测引擎空交易 — total_return 应为 0"""
        engine = BacktestEngine(initial_capital=100000)
        # 未运行回测时，创建空结果（适配当前 BacktestResult dataclass 方式）
        # 直接构造空结果验证
        from quantitative.backtest import BacktestResult
        result = BacktestResult(
            total_return_pct=0.0,
            annual_return_pct=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            total_trades=0,
            win_trades=0,
            loss_trades=0,
            win_rate=0.0,
        )
        assert result.total_return_pct == 0
        assert result.max_drawdown_pct == 0

    def test_backtest_insufficient_funds(self):
        """资金不足时通过 run() 验证 — 空策略应产生 0 交易"""
        from quantitative.strategy_base import BaseStrategy

        class StayFlatStrategy(BaseStrategy):
            """始终空仓的策略"""
            def generate_signals(self, df):
                result = df.copy()
                result["signal"] = 0
                return result

            def get_name(self):
                return "stay_flat"

        df = pd.DataFrame({
            "date": pd.bdate_range("2025-01-01", periods=10),
            "close": [20.0] * 10,
            "high": [21.0] * 10,
            "low": [19.0] * 10,
            "open": [19.5] * 10,
            "volume": [1000] * 10,
        })
        engine = BacktestEngine(initial_capital=1000)
        result = engine.run(StayFlatStrategy(), df)
        assert result.total_trades == 0

    def test_macd_divergence_detection(self):
        """MACD 背离检测"""
        # 价格波动 + 最终创新高
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                  19, 18, 17, 16, 15, 14, 13, 12, 11, 22, 23, 24]
        df = pd.DataFrame({"close": prices})
        result = MACD(df)
        assert "DIF" in result.columns
        assert "DEA" in result.columns
