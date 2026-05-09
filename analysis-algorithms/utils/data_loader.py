"""
数据加载工具
从 CSV 文件或直接通过采集器加载K线数据
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# 将项目根目录加入路径，方便直接引用 data-collector
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_csv(filepath: str) -> pd.DataFrame:
    """从 CSV 文件加载K线数据"""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    return _normalize_columns(df)


def load_from_collector(
    code: str,
    days: int = 365,
    source: str = "auto",
) -> pd.DataFrame:
    """通过 data-collector 直接采集数据"""
    try:
        from data_collector.crawler.stock_crawler import StockCrawler
        crawler = StockCrawler()
        df = crawler.fetch_kline(code, days=days, source=source, save=False)
        return df
    except ImportError:
        raise ImportError(
            "无法导入 data-collector。请确保 data-collector 在 PYTHONPATH 中"
        )
    except Exception as e:
        raise RuntimeError(f"数据采集失败: {e}")


def load_sample() -> pd.DataFrame:
    """加载示例数据用于测试"""
    sample_dir = PROJECT_ROOT / "data" / "samples"
    if not sample_dir.exists():
        # 生成示例数据
        return _generate_sample()
    csv_files = list(sample_dir.glob("*.csv"))
    if csv_files:
        return load_csv(str(csv_files[0]))
    return _generate_sample()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """统一列名: date, open, high, low, close, volume"""
    rename_map = {
        "trade_date": "date",
        "open_price": "open",
        "high_price": "high",
        "low_price": "low",
        "close_price": "close",
        "change_percent": "change_pct",
        "turnover_rate": "turnover",
    }
    df = df.rename(columns={c: rename_map[c] for c in df.columns if c in rename_map})

    # 确保关键列存在
    required = ["date", "open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"数据缺少必要列: {col}")

    # 排序
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _generate_sample() -> pd.DataFrame:
    """生成模拟K线数据（用于开发调试）"""
    import numpy as np

    np.random.seed(42)
    n = 120
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")

    # 模拟股价走势
    price = 10.0
    prices = []
    for _ in range(n):
        change = np.random.normal(0, 0.02)
        price *= (1 + change)
        prices.append(price)

    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        "high": [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        "low":  [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        "close": prices,
        "volume": np.random.randint(100000, 10000000, n),
    })
    df["open"] = df["open"].round(2)
    df["high"] = df["high"].round(2)
    df["low"] = df["low"].round(2)
    df["close"] = df["close"].round(2)
    return df
