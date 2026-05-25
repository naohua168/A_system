"""
资金流向回退采集器 — 使用腾讯财经数据估算

当东方财富 push2 API 不可用时，通过腾讯 qt.gtimg.cn 实时行情数据
(外盘/内盘/成交量/成交额) 估算个股资金流向。

腾讯返回格式: v_sz000001="51~名称~代码~现价~昨收~今开~成交量(手)~外盘~内盘~..."
"""
import logging
from datetime import datetime
from typing import List

import pandas as pd
import requests

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class FundFlowFallbackCollector(BaseCollector):
    """资金流向回退采集器 — 腾讯财经源"""

    source_name = "tencent_fallback"
    SUPPORTED_MARKETS = ["a_stock"]

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        })

    def fetch_fund_flow(self, code: str) -> pd.DataFrame:
        """通过腾讯实时行情估算资金流向

        Args:
            code: 股票代码 (如 "000001")

        Returns:
            DataFrame with columns: stock_code, trade_date, close,
            main_in, super_net_in, large_net_in, medium_net_in, little_net_in
        """
        market = "sz" if not code.startswith("6") else "sh"
        url = f"http://qt.gtimg.cn/q={market}{code}"
        try:
            r = self._session.get(url, timeout=10)
            text = r.text
        except Exception as e:
            logger.warning("[%s] 腾讯行情请求失败 [%s]: %s", self.source_name, code, e)
            return pd.DataFrame()

        # 解析腾讯返回数据
        # 格式: v_marketcode="fields~separated~by~tilde"
        if "=" not in text:
            return pd.DataFrame()
        data_part = text.split("=", 1)[1].strip().strip('"').strip(";").strip('"')
        fields = data_part.split("~")
        if len(fields) < 50:
            return pd.DataFrame()

        try:
            name = fields[1]
            price = self._safe_float(fields[3])
            prev_close = self._safe_float(fields[4])
            volume_hand = self._safe_float(fields[6])  # 成交量(手)
            outer_vol = self._safe_float(fields[7])     # 外盘
            inner_vol = self._safe_float(fields[8])     # 内盘
            amount = self._safe_float(fields[37]) if len(fields) > 37 else 0  # 成交额(万)
            change_pct = self._safe_float(fields[32]) if len(fields) > 32 else 0
        except (IndexError, ValueError):
            return pd.DataFrame()

        if price <= 0 or volume_hand <= 0:
            return pd.DataFrame()

        # 估算资金流向
        # 主力净流入 ≈ (外盘 - 内盘) × 均价 × 1000 (手转股)
        avg_price = amount * 10000 / (volume_hand * 100) if volume_hand > 0 else price
        main_in = (outer_vol - inner_vol) * avg_price

        # 按比例拆分到各级别（无法获知真实分布，使用典型比例）
        # 超大单 (>=100万) : 大单 (20-100万) : 中单 (4-20万) : 小单 (<4万)
        # 参考: 主力通常占 60-70%，散户占 30-40%
        abs_main = abs(main_in)
        super_ratio = 0.35
        large_ratio = 0.35
        medium_ratio = 0.20
        little_ratio = 0.10

        sign = 1 if main_in >= 0 else -1
        today = datetime.now().strftime("%Y-%m-%d")

        return pd.DataFrame([{
            "stock_code": code,
            "trade_date": today,
            "close": price,
            "change_pct": str(change_pct),
            "main_in": main_in,
            "super_net_in": sign * abs_main * super_ratio,
            "large_net_in": sign * abs_main * large_ratio,
            "medium_net_in": sign * abs_main * medium_ratio,
            "little_net_in": sign * abs_main * little_ratio,
            "source": self.source_name,
        }])

    @staticmethod
    def _safe_float(v) -> float:
        try:
            return float(v) if v not in ("", "-") else 0.0
        except (ValueError, TypeError):
            return 0.0

    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        raise NotImplementedError("请使用 TencentCollector")

    def health_check(self) -> bool:
        try:
            df = self.fetch_fund_flow("000001")
            return not df.empty
        except Exception:
            return False
