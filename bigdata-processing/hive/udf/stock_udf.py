"""Hive UDF 自定义函数 — 股票分析专用

使用方式 (Hive CLI):
  ADD JAR /path/to/stock_udf.py;
  CREATE TEMPORARY FUNCTION extract_code AS 'stock_udf.ExtractStockCode';
  SELECT extract_code(code) FROM stock_daily;
"""

import re
from datetime import datetime
from typing import Union


class ExtractStockCode:
    """提取标准化股票代码。
    Shell 模式 UDF：输入任意字符串，输出 6 位数字代码。
    """
    def evaluate(self, text: str) -> str:
        match = re.search(r"(\d{6})", str(text or ""))
        return match.group(1) if match else ""


class ClassifyChange:
    """涨跌幅分类。
    输入涨幅值 (float)，输出分类标签。
    """
    def evaluate(self, change_pct: Union[float, str]) -> str:
        try:
            val = float(change_pct)
        except (ValueError, TypeError):
            return "UNKNOWN"
        if val >= 9.8:
            return "涨停"
        elif val >= 5:
            return "大涨"
        elif val >= 2:
            return "上涨"
        elif val > -2:
            return "震荡"
        elif val > -5:
            return "下跌"
        elif val > -9.8:
            return "大跌"
        else:
            return "跌停"


class VolumeCompare:
    """成交量对比。
    输入今日/昨日成交量 (float)，输出放量/缩量/平量。
    """
    def evaluate(self, vol_today: Union[float, str], vol_yesterday: Union[float, str]) -> str:
        try:
            t = float(vol_today)
            y = float(vol_yesterday)
        except (ValueError, TypeError):
            return "UNKNOWN"
        if y <= 0:
            return "NODATA"
        ratio = t / y
        if ratio >= 1.5:
            return "放量"
        elif ratio <= 0.7:
            return "缩量"
        else:
            return "平量"


class TradeDate:
    """交易日判断。输入日期字符串，返回 WEEKDAY/WEEKEND/HOLIDAY。"""
    def evaluate(self, date_str: str) -> str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                dt = datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                return "INVALID"
        if dt.weekday() >= 5:
            return "WEEKEND"
        return "WEEKDAY"


class CapCategory:
    """市值分类。输入市值(亿元)，返回大盘/中盘/小盘/微盘。"""
    def evaluate(self, market_cap: Union[float, str]) -> str:
        try:
            cap = float(market_cap)
        except (ValueError, TypeError):
            return "UNKNOWN"
        if cap >= 1000:
            return "大盘"
        elif cap >= 200:
            return "中盘"
        elif cap >= 50:
            return "小盘"
        else:
            return "微盘"


# UDF 注册表 — 供 Hive 加载时自动发现
UDF_REGISTRY = {
    "extract_code": ExtractStockCode,
    "classify_change": ClassifyChange,
    "volume_compare": VolumeCompare,
    "trade_date": TradeDate,
    "cap_category": CapCategory,
}
