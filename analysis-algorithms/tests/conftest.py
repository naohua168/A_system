"""pytest 公共 Fixtures — L3 全量测试支持"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_kline(n=120, base_price=10.0, seed=42, use_trade_date=False):
    """生成 K 线 DataFrame

    Args:
        use_trade_date: True 时列名为 trade_date（模拟 MySQL stock_daily）
                        False 时列名为 date（模拟算法层内部格式）
    """
    np.random.seed(seed)
    dates = pd.bdate_range("2025-01-01", periods=n)
    trend = np.linspace(0, 2, n)
    noise = np.random.normal(0, 0.2, n).cumsum()
    closes = base_price + trend + noise
    date_col = "trade_date" if use_trade_date else "date"
    df = pd.DataFrame({
        date_col: dates,
        "open": closes - np.random.uniform(0, 0.3, n),
        "high": closes + np.random.uniform(0, 0.5, n),
        "low": closes - np.random.uniform(0, 0.5, n),
        "close": closes,
        "volume": np.random.randint(500000, 5000000, n),
        "amount": np.random.uniform(5000, 50000, n) * 10000,
        "change_pct": np.random.uniform(-5, 5, n),
        "turnover_pct": np.random.uniform(0.5, 10, n),
    })
    if use_trade_date:
        df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].round(2)
    df[["volume"]] = df[["volume"]].astype(int)
    return df


@pytest.fixture(scope="session")
def sample_data():
    """标准样本（date 列名，120 条）"""
    return _make_kline(n=120)


@pytest.fixture(scope="session")
def sample_data_trade_date():
    """MySQL 风格样本（trade_date 列名，120 条）"""
    return _make_kline(n=120, use_trade_date=True)


@pytest.fixture(scope="session")
def small_sample(sample_data):
    return sample_data.iloc[:20].copy()


@pytest.fixture(scope="session")
def long_sample():
    return _make_kline(n=252, seed=123)


@pytest.fixture
def engine():
    """分析引擎（不连 MySQL，测试需 mock loader）"""
    from engine.orchestrator import AnalysisEngine
    eng = AnalysisEngine()
    eng.loader._mysql_conn = None
    eng.loader._redis_client = None
    return eng
