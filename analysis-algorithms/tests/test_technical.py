"""
技术指标单元测试（pytest 版本）
验证 MA/MACD/KDJ/RSI/BOLL 计算正确性
"""

import pytest
import pandas as pd
import numpy as np

# 导入被测试模块
from technical import MA, MACD, KDJ, RSI, BollingerBands, calculate_all


class TestMA:
    """移动平均线测试"""

    def test_ma_returns_expected_columns(self, sample_data):
        df = MA(sample_data)
        assert "MA5" in df.columns
        assert "MA20" in df.columns

    def test_ma5_correct_value(self, sample_data):
        df = MA(sample_data)
        # 前 4 个值应为 NaN（MA5 需要 5 个数据点）
        assert df["MA5"].iloc[:4].isna().all()
        # 第 5 个值应为前 5 个收盘价的均值
        expected_ma5 = sample_data["close"].iloc[:5].mean()
        assert df["MA5"].iloc[4] == pytest.approx(expected_ma5, rel=1e-2)

    def test_ma_length_preserved(self, sample_data):
        df = MA(sample_data)
        assert len(df) == len(sample_data)

    def test_ma_empty_input(self):
        empty_df = pd.DataFrame()
        with pytest.raises(Exception):
            MA(empty_df)


class TestMACD:
    """MACD 指标测试"""

    def test_macd_returns_expected_columns(self, sample_data):
        df = MACD(sample_data)
        assert "DIF" in df.columns
        assert "DEA" in df.columns
        assert "MACD" in df.columns

    def test_macd_values_in_range(self, sample_data):
        df = MACD(sample_data)
        last = df.iloc[-1]
        # DIF 和 DEA 应为有限数值
        assert np.isfinite(last["DIF"])
        assert np.isfinite(last["DEA"])

    def test_macd_is_dif_minus_dea(self, sample_data):
        df = MACD(sample_data)
        for idx in range(26, len(df)):
            expected_macd = 2 * (df["DIF"].iloc[idx] - df["DEA"].iloc[idx])
            assert df["MACD"].iloc[idx] == pytest.approx(expected_macd, rel=1e-2)


class TestKDJ:
    """KDJ 指标测试"""

    def test_kdj_returns_expected_columns(self, sample_data):
        df = KDJ(sample_data)
        assert "K" in df.columns
        assert "D" in df.columns

    def test_kdj_values_in_0_100_range(self, sample_data):
        df = KDJ(sample_data)
        # K/D 值应在 0~100 之间
        assert df["K"].dropna().between(0, 100).all()
        assert df["D"].dropna().between(0, 100).all()


class TestRSI:
    """RSI 指标测试"""

    def test_rsi_returns_expected_columns(self, sample_data):
        df = RSI(sample_data)
        assert "RSI6" in df.columns
        assert "RSI12" in df.columns

    def test_rsi_range(self, sample_data):
        df = RSI(sample_data)
        # RSI 应在 0~100 之间
        assert df["RSI6"].dropna().between(0, 100).all()


class TestBollinger:
    """布林带测试"""

    def test_bollinger_returns_expected_columns(self, sample_data):
        df = BollingerBands(sample_data)
        assert "BOLL_MID" in df.columns
        assert "BOLL_UP" in df.columns
        assert "BOLL_DOWN" in df.columns

    def test_bollinger_bands_ordered(self, sample_data):
        df = BollingerBands(sample_data)
        last = df.dropna().iloc[-1]
        assert last["BOLL_UP"] > last["BOLL_MID"] > last["BOLL_DOWN"]

    def test_bollinger_mid_is_ma20(self, sample_data):
        df = BollingerBands(sample_data)
        df_ma = MA(sample_data)
        # 中轨 = MA20
        for idx in df.dropna().index:
            assert df.loc[idx, "BOLL_MID"] == pytest.approx(df_ma.loc[idx, "MA20"], rel=1e-2)


class TestCalculateAll:
    """一键计算全部指标测试"""

    def test_all_indicators_present(self, sample_data):
        df = calculate_all(sample_data)
        expected_cols = ["MA5", "MA20", "DIF", "MACD", "K", "D", "RSI6", "RSI12", "BOLL_MID", "BOLL_UP"]
        for col in expected_cols:
            assert col in df.columns, f"缺少列: {col}"

    def test_no_missing_columns(self, sample_data):
        df = calculate_all(sample_data)
        # 所有列都应该存在，无 NaN 列名
        assert df.columns.isna().sum() == 0
