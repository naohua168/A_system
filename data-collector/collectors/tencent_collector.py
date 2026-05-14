"""
腾讯财经 API 采集器
覆盖：PE(TTM)/PB/总市值/流通市值/换手率/涨跌停价/量比
数据特点：HTTP GET，GBK编码，不封IP，无需注册

字段索引（实测校准）:
  39=PE(TTM), 43=振幅%, 44=总市值(亿), 45=流通市值(亿)
  46=PB, 47=涨停价, 48=跌停价, 52=PE(静)
"""
import urllib.request
from typing import List, Optional

import pandas as pd

from .base_collector import BaseCollector


class TencentCollector(BaseCollector):
    """腾讯财经数据源 — PE/PB/市值/涨跌停价"""

    source_name = "tencent"
    SUPPORTED_MARKETS = ["a_stock"]

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """批量获取腾讯财经实时行情"""
        prefixed = []
        for c in codes:
            if c.startswith(("6", "9")):
                prefixed.append(f"sh{c}")
            elif c.startswith("8"):
                prefixed.append(f"bj{c}")
            else:
                prefixed.append(f"sz{c}")

        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")

        try:
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read().decode("gbk")
        except Exception as e:
            raise RuntimeError(f"腾讯财经请求失败: {e}")

        records = []
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            try:
                records.append({
                    "code": code, "name": vals[1],
                    "price": float(vals[3]) if vals[3] else 0,
                    "last_close": float(vals[4]) if vals[4] else 0,
                    "open": float(vals[5]) if vals[5] else 0,
                    "high": float(vals[33]) if vals[33] else 0,
                    "low": float(vals[34]) if vals[34] else 0,
                    "change_amt": float(vals[31]) if vals[31] else 0,
                    "change_pct": float(vals[32]) if vals[32] else 0,
                    "amount_wan": float(vals[37]) if vals[37] else 0,
                    "turnover_pct": float(vals[38]) if vals[38] else 0,
                    "pe_ttm": float(vals[39]) if vals[39] else 0,
                    "amplitude_pct": float(vals[43]) if vals[43] else 0,
                    "mcap_yi": float(vals[44]) if vals[44] else 0,
                    "float_mcap_yi": float(vals[45]) if vals[45] else 0,
                    "pb": float(vals[46]) if vals[46] else 0,
                    "limit_up": float(vals[47]) if vals[47] else 0,
                    "limit_down": float(vals[48]) if vals[48] else 0,
                    "vol_ratio": float(vals[49]) if vals[49] else 0,
                    "pe_static": float(vals[52]) if vals[52] else 0,
                    "source": self.source_name,
                    "timestamp": pd.Timestamp.now(),
                })
            except (ValueError, IndexError):
                continue
        return pd.DataFrame(records)

    def fetch_stock_basic(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        df = self.fetch_all_realtime()
        if df.empty:
            return df
        result = df[["code", "name", "pe_ttm", "pb", "mcap_yi",
                      "turnover_pct", "source"]].copy()
        if codes and codes[0] != "*":
            result = result[result["code"].isin(codes)]
        return result

    def fetch_all_realtime(self) -> pd.DataFrame:
        """获取全市场实时行情"""
        codes = []
        for prefix in ["sh6", "sz0", "sz3", "sh9", "bj4", "bj8"]:
            for i in range(0, 1000):
                codes.append(f"{prefix}{i:06d}")
        all_records = []
        batch_size = 100
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            url = "https://qt.gtimg.cn/q=" + ",".join(batch)
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "Mozilla/5.0")
                resp = urllib.request.urlopen(req, timeout=15)
                data = resp.read().decode("gbk")
                for line in data.strip().split(";"):
                    if not line.strip() or "=" not in line or '"' not in line:
                        continue
                    key = line.split("=")[0].split("_")[-1]
                    vals = line.split('"')[1].split("~")
                    if len(vals) < 53:
                        continue
                    code = key[2:]
                    try:
                        all_records.append({
                            "code": code, "name": vals[1],
                            "price": float(vals[3]) if vals[3] else 0,
                            "change_pct": float(vals[32]) if vals[32] else 0,
                            "pe_ttm": float(vals[39]) if vals[39] else 0,
                            "pb": float(vals[46]) if vals[46] else 0,
                            "mcap_yi": float(vals[44]) if vals[44] else 0,
                            "turnover_pct": float(vals[38]) if vals[38] else 0,
                            "source": self.source_name,
                        })
                    except (ValueError, IndexError):
                        continue
            except Exception:
                continue
        return pd.DataFrame(all_records)

    def health_check(self) -> bool:
        try:
            df = self.fetch_realtime_quotes(["000001"])
            return not df.empty
        except Exception:
            return False

    def fetch_history_kline(
        self, code: str, start_date: Optional[str] = None,
        end_date: Optional[str] = None, freq: str = "daily",
    ) -> pd.DataFrame:
        """腾讯财经不提供K线数据"""
        raise NotImplementedError("腾讯财经不提供K线数据，请使用 mootdx 数据源")
