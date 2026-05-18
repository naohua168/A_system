"""AI 服务通用工具函数"""
import re
from datetime import datetime, timedelta


def extract_stock_code(text: str) -> str:
    """从文本中提取6位股票代码"""
    match = re.search(r"(\d{6})", text)
    return match.group(1) if match else ""


def extract_fund_code(text: str) -> str:
    """从文本中提取6位基金代码（通常以 0、1、5、6、9 开头）"""
    match = re.search(r"(\b[01569]\d{5}\b)", text)
    return match.group(1) if match else ""


def safe_float(value, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_change(value: float) -> str:
    """格式化涨跌幅，如 +3.25% / -1.50%"""
    if value >= 0:
        return f"+{value:.2f}%"
    return f"{value:.2f}%"


def truncate(text: str, max_len: int = 200) -> str:
    """截断文本并添加省略号"""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def time_ago(dt: datetime) -> str:
    """返回相对时间描述"""
    now = datetime.now()
    diff = now - dt
    if diff.days > 365:
        return f"{diff.days // 365}年前"
    if diff.days > 30:
        return f"{diff.days // 30}月前"
    if diff.days > 0:
        return f"{diff.days}天前"
    if diff.seconds >= 3600:
        return f"{diff.seconds // 3600}小时前"
    if diff.seconds >= 60:
        return f"{diff.seconds // 60}分钟前"
    return "刚刚"


def parse_trade_date(date_str: str) -> datetime | None:
    """解析交易日期字符串（兼容多种格式）"""
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d",
        "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def is_trade_time(dt: datetime | None = None) -> bool:
    """判断是否在交易时间段内（9:30-11:30, 13:00-15:00）"""
    if dt is None:
        dt = datetime.now()
    if dt.weekday() >= 5:
        return False  # 周末休市
    t = dt.hour * 100 + dt.minute
    return (930 <= t <= 1130) or (1300 <= t <= 1500)
