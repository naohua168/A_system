"""
日期工具函数
交易日判断、日期格式化、日期范围生成等
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple


def parse_date(date_str: str) -> datetime:
    """解析多种格式的日期字符串为 datetime"""
    formats = [
        "%Y%m%d", "%Y-%m-%d", "%Y/%m/%d",
        "%Y%m%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_str}")


def format_date(dt: datetime, fmt: str = "%Y%m%d") -> str:
    """格式化日期"""
    return dt.strftime(fmt)


def generate_date_range(
    start: str, end: str, step_days: int = 1
) -> list[str]:
    """生成日期列表"""
    dates = []
    current = parse_date(start)
    end_dt = parse_date(end)
    while current <= end_dt:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=step_days)
    return dates


def split_date_range(
    start_date: str,
    end_date: str,
    chunk_months: int = 3,
) -> list[Tuple[str, str]]:
    """将长日期范围按月份分割成多个短区间（用于分批拉取）"""
    start = parse_date(start_date)
    end = parse_date(end_date)

    chunks = []
    current = start
    while current < end:
        chunk_end = datetime(
            year=current.year + (current.month + chunk_months - 1) // 12,
            month=(current.month + chunk_months - 1) % 12 + 1,
            day=1,
        ) - timedelta(days=1)
        if chunk_end > end:
            chunk_end = end
        chunks.append((
            current.strftime("%Y%m%d"),
            chunk_end.strftime("%Y%m%d"),
        ))
        current = chunk_end + timedelta(days=1)

    return chunks


def is_trading_day(dt: Optional[datetime] = None) -> bool:
    """简单判断是否为交易日（排除周末）"""
    dt = dt or datetime.now()
    return dt.weekday() < 5  # 0=周一, ..., 4=周五


def get_last_trading_day(dt: Optional[datetime] = None) -> str:
    """获取最近一个交易日"""
    dt = dt or datetime.now()
    while not is_trading_day(dt):
        dt -= timedelta(days=1)
    return dt.strftime("%Y%m%d")


def get_today_str(fmt: str = "%Y%m%d") -> str:
    """获取今天日期字符串"""
    return datetime.now().strftime(fmt)
