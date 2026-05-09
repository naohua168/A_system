"""
pytest 公共 Fixtures
为 analysis-algorithms 模块提供共享的测试数据
"""

import sys
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


@pytest.fixture(scope="session")
def sample_data():
    """生成 120 条模拟日K线数据（约 6 个月交易数据）"""
    np.random.seed(42)
    n = 120
    dates = pd.bdate_range("2025-01-01", periods=n)

    # 模拟股价：初始 10 元，加入趋势 + 随机波动
    base = 10.0
    trend = np.linspace(0, 2, n)
    noise = np.random.normal(0, 0.2, n).cumsum()
    closes = base + trend + noise

    # 生成 OHLC
    df = pd.DataFrame({
        "date": dates,
        "open": closes - np.random.uniform(0, 0.3, n),
        "high": closes + np.random.uniform(0, 0.5, n),
        "low": closes - np.random.uniform(0, 0.5, n),
        "close": closes,
        "volume": np.random.randint(500000, 5000000, n),
    })
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].round(2)
    return df


@pytest.fixture(scope="session")
def small_sample(sample_data):
    """小样本数据（20 条）"""
    return sample_data.iloc[:20].copy()
