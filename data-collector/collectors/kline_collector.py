"""
多周期K线采集器 — 支持8种周期
数据源: 新浪财经(优先), 腾讯财经(备用)
周期: 1min, 5min, 15min, 30min, 60min, 日K, 周K, 月K
"""
import json, logging, time
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import requests

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# 新浪 scale 参数映射
SINA_SCALE = {
    "1min": 1, "5min": 5, "15min": 15,
    "30min": 30, "60min": 60, "daily": 240,
}

# 腾讯 period 参数映射
TENCENT_PERIOD = {
    "1min": "m1", "5min": "m5", "15min": "m15",
    "30min": "m30", "60min": "m60",
    "daily": "d", "weekly": "w", "monthly": "mon",
}

class KlineCollector(BaseCollector):
    """多周期K线采集器 — 新浪财经 + 腾讯财经"""

    source_name = "kline"
    SUPPORTED_MARKETS = ["a_stock"]

    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Referer": "https://finance.sina.com.cn/",
    }

    def __init__(self):
        super().__init__()
        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)

    def fetch_kline(self, code: str, freq: str = "daily",
                    days: int = 365) -> pd.DataFrame:
        """
        采集多周期K线数据

        Args:
            code: 6位股票代码
            freq: 周期 (1min/5min/15min/30min/60min/daily/weekly/monthly)
            days: 回溯天数（仅对日K及以上有效）
        Returns:
            DataFrame: date, open, high, low, close, volume, amount
        """
        # 周K/月K 从日K聚合
        if freq in ("weekly", "monthly"):
            daily = self.fetch_kline(code, "daily", days)
            if daily.empty:
                return daily
            return self._aggregate_to(daily, freq)

        # 分钟K/日K 优先新浪
        df = self._fetch_from_sina(code, freq)
        if not df.empty:
            df["code"] = code
            df["freq"] = freq
            return df

        # 回退腾讯
        df = self._fetch_from_tencent(code, freq)
        if not df.empty:
            df["code"] = code
            df["freq"] = freq
            return df

        return pd.DataFrame()

    def _fetch_from_sina(self, code: str, freq: str) -> pd.DataFrame:
        """新浪财经K线"""
        scale = SINA_SCALE.get(freq)
        if scale is None:
            return pd.DataFrame()

        prefix = "sz" if code[0] in ("0", "3") else "sh"
        url = (
            f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"CN_MarketData.getKLineData?symbol={prefix}{code}"
            f"&scale={scale}&ma=0&datalen=1023"
        )
        try:
            r = self._session.get(url, timeout=10)
            if r.status_code != 200 or len(r.text) < 50:
                return pd.DataFrame()
            data = json.loads(r.text)
            records = []
            for item in data:
                records.append({
                    "date": item["day"],
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": int(float(item.get("volume", 0))),
                })
            df = pd.DataFrame(records)
            if not df.empty:
                df["source"] = "sina"
                logger.info("[新浪] %s %s: %d行", code, freq, len(df))
            return df
        except Exception as e:
            logger.warning("[新浪] %s %s失败: %s", code, freq, e)
            return pd.DataFrame()

    def _fetch_from_tencent(self, code: str, freq: str) -> pd.DataFrame:
        """腾讯财经K线"""
        period = TENCENT_PERIOD.get(freq)
        if period is None:
            return pd.DataFrame()

        prefix = "sz" if code[0] in ("0", "3") else "sh"
        url = f"http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={prefix}{code},{period},,320"
        try:
            r = self._session.get(url, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                return pd.DataFrame()
            d = r.json()
            if d.get("code") != 0:
                return pd.DataFrame()
            # 解析腾讯返回格式
            data_key = f"{prefix}{code}"
            kline_data = d.get("data", {}).get(data_key, {})
            # 腾讯不同周期key不同
            for key in [period, period.replace("m","m"), "qfq"+period, period+"qfq"]:
                if key in kline_data:
                    items = kline_data[key]
                    break
            else:
                items = kline_data.get(period, [])
            records = []
            for item in items:
                if isinstance(item, list) and len(item) >= 6:
                    records.append({
                        "date": item[0],
                        "open": float(item[1]),
                        "close": float(item[2]),
                        "high": float(item[3]),
                        "low": float(item[4]),
                        "volume": int(float(item[5])) if item[5] else 0,
                    })
            df = pd.DataFrame(records)
            if not df.empty:
                df["source"] = "tencent"
                logger.info("[腾讯] %s %s: %d行", code, freq, len(df))
            return df
        except Exception as e:
            logger.warning("[腾讯] %s %s失败: %s", code, freq, e)
            return pd.DataFrame()

    def _aggregate_to(self, daily_df: pd.DataFrame, target: str) -> pd.DataFrame:
        """从日K聚合生成周K/月K"""
        df = daily_df.copy()
        df["date"] = pd.to_datetime(df["date"])

        if target == "weekly":
            df["period"] = df["date"].dt.isocalendar().year.astype(str) + "-W" + df["date"].dt.isocalendar().week.astype(str).str.zfill(2)
        elif target == "monthly":
            df["period"] = df["date"].dt.to_period("M").astype(str)
        else:
            return pd.DataFrame()

        def agg(group):
            return pd.Series({
                "date": group.name,
                "open": group.iloc[0]["open"],
                "high": group["high"].max(),
                "low": group["low"].min(),
                "close": group.iloc[-1]["close"],
                "volume": group["volume"].sum(),
                "source": "aggregated",
                "freq": target,
            })

        result = df.groupby("period", sort=False).apply(agg, include_groups=False).reset_index()
        result = result.rename(columns={"period": "period_label"})
        # 按时间排序
        if target == "weekly":
            result["_sort"] = result["period_label"].apply(
                lambda x: x.split("-W")[0] + x.split("-W")[1] if "-W" in str(x) else str(x))
        else:
            result["_sort"] = result["period_label"]
        result = result.sort_values("_sort")
        result["date"] = result["period_label"]
        result = result.drop(columns=["period_label", "_sort"])
        logger.info("[聚合] 日K→%s: %d行", target, len(result))
        return result

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """从腾讯获取实时行情（用于1分钟K实时生成）"""
        return pd.DataFrame()

    def health_check(self) -> bool:
        try:
            df = self.fetch_kline("000001", "daily", 5)
            return not df.empty
        except:
            return False
