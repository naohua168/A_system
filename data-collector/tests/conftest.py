"""
data-collector pytest 公共 Fixtures
提供模拟数据，避免真实网络请求
"""

import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


@pytest.fixture
def mock_kline_data():
    """模拟日K线数据（不依赖网络）"""
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=30, freq="B"),
        "open": [10.0 + i * 0.1 for i in range(30)],
        "high": [10.5 + i * 0.1 for i in range(30)],
        "low": [9.8 + i * 0.1 for i in range(30)],
        "close": [10.2 + i * 0.1 for i in range(30)],
        "volume": [1000000 + i * 10000 for i in range(30)],
    })


@pytest.fixture
def mock_realtime_data():
    """模拟实时行情数据"""
    return pd.DataFrame({
        "code": ["000001", "600519", "300750"],
        "name": ["平安银行", "贵州茅台", "宁德时代"],
        "price": [12.5, 1500.0, 180.0],
        "change_pct": [1.2, 0.8, -0.5],
        "volume": [5000000, 200000, 1000000],
    })


@pytest.fixture
def mock_collector(mocker):
    """模拟数据采集器"""
    collector = mocker.MagicMock()
    collector.health_check.return_value = True
    collector.fetch_history_kline.return_value = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=10, freq="B"),
        "close": [10.0 + i * 0.1 for i in range(10)],
    })
    collector.fetch_realtime_quotes.return_value = pd.DataFrame({
        "code": ["000001"],
        "price": [12.5],
    })
    return collector
