"""
数据采集器抽象基类
定义统一的数据采集接口，所有数据源采集器必须继承此类
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from config import MAX_RETRIES, RETRY_BACKOFF_BASE, RETRY_BACKOFF_MAX, VALIDATION

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """数据质量校验失败"""
    pass


class CircuitBreakerOpenError(Exception):
    """熔断器已打开，暂不执行"""
    pass


class CircuitBreaker:
    """简易熔断器 — 防止对已故障数据源重复重试"""

    # 类级状态（所有实例共享同源信息）
    _state: dict = {}

    def __init__(self, source_name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60):
        self.source_name = source_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        if source_name not in self._state:
            self._state[source_name] = {
                "state": "closed",         # closed / open / half_open
                "failure_count": 0,
                "last_failure_time": 0,
                "half_open_attempts": 0,
            }

    @property
    def _s(self):
        return self._state[self.source_name]

    def allow_request(self) -> bool:
        """判断是否允许请求通过"""
        state = self._s["state"]
        if state == "closed":
            return True
        if state == "open":
            elapsed = time.time() - self._s["last_failure_time"]
            if elapsed >= self.recovery_timeout:
                self._s["state"] = "half_open"
                self._s["half_open_attempts"] = 0
                logger.info("熔断器 [%s] 进入半开状态", self.source_name)
                return True
            return False
        # half_open
        if self._s["half_open_attempts"] < 3:
            self._s["half_open_attempts"] += 1
            return True
        return False

    def record_success(self):
        """记录成功，关闭熔断器"""
        self._s["state"] = "closed"
        self._s["failure_count"] = 0
        self._s["half_open_attempts"] = 0

    def record_failure(self):
        """记录失败"""
        self._s["failure_count"] += 1
        self._s["last_failure_time"] = time.time()
        if self._s["failure_count"] >= self.failure_threshold:
            self._s["state"] = "open"
            logger.warning("熔断器 [%s] 已打开 (连续失败 %d 次)",
                           self.source_name, self._s["failure_count"])


class BaseCollector(ABC):
    """数据采集器基类 — 策略模式中的 Strategy 接口"""

    # 数据源唯一标识
    source_name: str = "base"

    # 支持的数据类型
    SUPPORTED_MARKETS = ["a_stock", "hk_stock", "us_stock", "fund", "index"]

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._last_result: Optional[pd.DataFrame] = None
        self._last_fetch_time: Optional[datetime] = None
        self._circuit_breaker = CircuitBreaker(
            self.source_name,
            failure_threshold=config.get("circuit_breaker", {}).get("failure_threshold", 5)
            if config else 5,
            recovery_timeout=config.get("circuit_breaker", {}).get("recovery_timeout", 60)
            if config else 60,
        )

    # -----------------------------------------------------------
    # 抽象方法 — 子类必须实现
    # -----------------------------------------------------------

    @abstractmethod
    def fetch_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情
        Args:
            codes: 股票代码列表，如 ["000001", "600519"]
        Returns:
            DataFrame with columns: code, name, price, change, change_pct, volume, amount, timestamp
        """
        ...

    # -----------------------------------------------------------
    # 可选方法 — 部分数据源可实现（不是所有采集器都提供K线）
    # -----------------------------------------------------------

    def fetch_history_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = "daily",
    ) -> pd.DataFrame:
        """获取历史K线数据（部分数据源不支持此接口）
        Args:
            code: 股票代码
            start_date: 起始日期 YYYYMMDD，默认2年前
            end_date: 结束日期 YYYYMMDD，默认今天
            freq: K线频率 daily/weekly/monthly
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        raise NotImplementedError(f"{self.source_name} 不提供历史K线数据")

    def fetch_fund_nav(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取基金净值数据（可选实现）"""
        raise NotImplementedError(f"{self.source_name} 不支持基金净值查询")

    # -----------------------------------------------------------
    # 重试机制 — 指数退避重试
    # -----------------------------------------------------------

    def _retry_with_backoff(
        self,
        func,
        *args,
        max_retries: int = MAX_RETRIES,
        backoff_base: float = RETRY_BACKOFF_BASE,
        backoff_max: float = RETRY_BACKOFF_MAX,
        **kwargs,
    ):
        """指数退避重试装饰器
        策略: 1s → 2s → 4s → 8s → max, 触发熔断后不再重试
        """
        last_exc = None
        for attempt in range(max_retries + 1):
            # 熔断检查
            if not self._circuit_breaker.allow_request():
                raise CircuitBreakerOpenError(
                    f"熔断器 [{self.source_name}] 已打开，跳过请求"
                )

            try:
                result = func(*args, **kwargs)
                self._circuit_breaker.record_success()
                self._last_fetch_time = datetime.now()
                return result
            except CircuitBreakerOpenError:
                raise
            except Exception as e:
                last_exc = e
                self._circuit_breaker.record_failure()
                if attempt < max_retries:
                    delay = min(backoff_base * (2 ** attempt), backoff_max)
                    logger.warning(
                        "[%s] 第 %d 次重试 (等待 %.1fs): %s",
                        self.source_name, attempt + 1, delay, e,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "[%s] 重试 %d 次全部失败: %s",
                        self.source_name, max_retries, e,
                    )
        raise RuntimeError(f"[{self.source_name}] 采集失败: {last_exc}")

    # -----------------------------------------------------------
    # 数据校验
    # -----------------------------------------------------------

    def validate_realtime_row(self, row: dict) -> dict:
        """校验单行实时行情数据的合法性与合理性"""
        # 修复: 增加 None 检查，避免 dict(row) 抛出 TypeError
        if row is None:
            raise DataQualityError("输入行数据为 None")
        validated = dict(row)

        # 价格合法性
        price = validated.get("price", 0)
        if not isinstance(price, (int, float)) or price < VALIDATION["price_min"]:
            raise DataQualityError(f"非法价格: {price}")

        # 涨跌幅合理性
        change_pct = validated.get("change_pct", 0)
        if not (VALIDATION["change_pct_min"] <= change_pct <= VALIDATION["change_pct_max"]):
            raise DataQualityError(f"非法涨跌幅: {change_pct}%")

        return validated

    def validate_dataframe(self, df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
        """校验 DataFrame 数据质量，过滤异常行

        Returns:
            清洗后的 DataFrame
        """
        if df.empty:
            return df

        # 检查必选列
        missing_cols = [c for c in required_columns if c not in df.columns]
        if missing_cols:
            raise DataQualityError(f"缺少必选列: {missing_cols}")

        # 检查空值比例
        # 修复: 从 config 读取空值阈值，而非硬编码 0.5
        max_null_ratio = VALIDATION.get("max_null_ratio", 0.5)
        for col in required_columns:
            null_ratio = df[col].isna().sum() / len(df)
            if null_ratio > max_null_ratio and col not in VALIDATION.get("nullable_columns", []):
                logger.warning("[%s] 列 '%s' 空值比例 %.1f%% (阈值 %.0f%%)",
                               self.source_name, col, null_ratio * 100, max_null_ratio * 100)

        return df

    # -----------------------------------------------------------
    # 通用工具方法
    # -----------------------------------------------------------

    def _default_date_range(self, years: int = 2) -> tuple:
        """生成默认的日期范围 (start_date, end_date)"""
        end = datetime.now()
        start = end - timedelta(days=int(years * 365))
        return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    def save_to_csv(self, df: pd.DataFrame, filepath: str) -> str:
        """保存 DataFrame 到 CSV 文件"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        self._last_result = df
        return str(path)

    def get_last_result(self) -> Optional[pd.DataFrame]:
        """获取最近一次采集结果"""
        return self._last_result

    def get_freshness(self) -> Optional[float]:
        """获取数据新鲜度（距上次成功采集的秒数），None 表示从未采集"""
        if self._last_fetch_time is None:
            return None
        return (datetime.now() - self._last_fetch_time).total_seconds()

    def health_check(self) -> bool:
        """健康检查 — 检测数据源是否可达（走熔断器保护）"""
        try:
            return self._retry_with_backoff(
                self._do_health_check
            )
        except Exception:
            return False

    def _do_health_check(self) -> bool:
        """实际健康检查逻辑，子类可覆盖"""
        df = self.fetch_realtime_quotes(["000001"])
        return not df.empty
