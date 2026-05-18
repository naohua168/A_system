"""
分析引擎统一调度器 — 编排数据分析全流程

新架构下的分析流程:
  数据源层     →    计算层     →    存储层     →    展示层
  MySQL/HDFS        Pandas/Spark      MySQL/Redis      Backend API

职责:
  1. 从存储层加载 K 线 + 指标 + 信号数据
  2. 执行本地未预计算的分析（如缠论、量化回测）
  3. 将分析结果写回 MySQL + Redis 缓存
  4. 返回结构化结果给后端 API

与旧架构的区别:
  - 旧: 分析算法直接调用采集器 / 读 CSV（紧耦合）
  - 新: 分析算法统一从存储层读取，分析结果写回存储层
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from utils.data_loader import DataLoader

logger = logging.getLogger("analysis.engine")


class AnalysisEngine:
    """统一分析引擎"""

    def __init__(self, mysql_config: dict = None, redis_host: str = "localhost"):
        self.loader = DataLoader(mysql_config, redis_host)
        self._redis = None

    # ============================
    # Redis 缓存
    # ============================

    @property
    def redis(self):
        if self._redis is None:
            try:
                import redis as _redis
                self._redis = _redis.Redis(host=self.loader._redis_host, port=6379,
                                           decode_responses=True, socket_timeout=3)
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def _cache_get(self, key: str) -> Optional[str]:
        try:
            if self.redis:
                return self.redis.get(f"analysis:{key}")
        except Exception:
            pass
        return None

    def _cache_set(self, key: str, value: str, ttl: int = 300):
        try:
            if self.redis:
                self.redis.setex(f"analysis:{key}", ttl, value)
        except Exception:
            pass

    # ============================
    # 全量股票分析（单只）
    # ============================

    def analyze_stock(self, code: str, days: int = 365,
                      with_chanlun: bool = True,
                      with_quantitative: bool = True) -> dict:
        """单只股票全量分析

        返回: {
            "stock_code", "stock_name",
            "realtime",              # 实时行情
            "kline",                 # K线概览
            "technical": {           # 技术指标
                "ma", "macd", "rsi", "bollinger", "kdj"
            },
            "signals": {             # 信号层
                "hot_reason", "northbound", "fund_flow",
                "dragon_tiger", "concept", "lockup"
            },
            "chanlun": {...},        # 缠论分析（可选）
            "quantitative": {...},   # 量化信号（可选）
            "analysis_time"
        }
        """
        cache_key = f"full:{code}:{days}"
        cached = self._cache_get(cache_key)
        if cached:
            return json.loads(cached)

        t0 = time.time()
        result = {
            "stock_code": code,
            "analysis_time": datetime.now().isoformat(),
        }

        # 1. 实时行情
        result["realtime"] = self.loader.read_realtime(code)

        # 2. K 线数据
        kline = self.loader.read_kline(code, days)
        if not kline.empty:
            result["kline"] = {
                "count": len(kline),
                "start_date": kline["date"].iloc[0],
                "end_date": kline["date"].iloc[-1],
                "latest": kline.tail(5).to_dict("records"),
            }

        # 3. 技术指标（优先读 Spark 预计算结果）
        result["technical"] = self._analyze_technical(code, kline)

        # 4. 信号层
        result["signals"] = self._load_signals(code)

        # 5. 缠论分析
        if with_chanlun and not kline.empty:
            result["chanlun"] = self._analyze_chanlun(kline)

        # 6. 量化回测信号
        if with_quantitative and not kline.empty:
            result["quantitative"] = self._analyze_quantitative(kline)

        result["elapsed_ms"] = round((time.time() - t0) * 1000, 1)

        # 缓存 5 分钟
        self._cache_set(cache_key, json.dumps(result, ensure_ascii=False, default=str), 300)
        return result

    # ============================
    # 技术指标分析
    # ============================

    def _analyze_technical(self, code: str, kline: pd.DataFrame) -> dict:
        """技术指标分析

        优先读取 Spark 预计算结果，无则本地计算
        """
        technical = {}

        # 1. 移动平均线
        ma_df = self.loader.read_indicators(code, "ma")
        if not ma_df.empty:
            technical["ma"] = ma_df.to_dict("records")
        elif not kline.empty:
            from technical.ma import MA
            technical["ma"] = MA(kline).tail(10).to_dict("records")

        # 2. MACD
        macd_df = self.loader.read_indicators(code, "macd")
        if not macd_df.empty:
            technical["macd"] = macd_df.to_dict("records")
        elif not kline.empty:
            from technical.macd import MACD, macd_signal
            technical["macd"] = macd_signal(MACD(kline)).tail(10).to_dict("records")

        # 3. RSI
        rsi_df = self.loader.read_indicators(code, "rsi")
        if not rsi_df.empty:
            technical["rsi"] = rsi_df.to_dict("records")
        elif not kline.empty:
            from technical.rsi import RSI
            technical["rsi"] = RSI(kline).tail(10).to_dict("records")

        # 4. 布林带
        boll_df = self.loader.read_indicators(code, "bollinger")
        if not boll_df.empty:
            technical["bollinger"] = boll_df.to_dict("records")
        elif not kline.empty:
            from technical.bollinger import BOLL
            technical["bollinger"] = BOLL(kline).tail(10).to_dict("records")

        # 5. KDJ
        kdj_df = self.loader.read_indicators(code, "kdj")
        if not kdj_df.empty:
            technical["kdj"] = kdj_df.to_dict("records")
        elif not kline.empty:
            from technical.kdj import KDJ
            technical["kdj"] = KDJ(kline).tail(10).to_dict("records")

        return technical

    # ============================
    # 信号层数据
    # ============================

    def _load_signals(self, code: str) -> dict:
        """加载信号层数据"""
        signals = {}
        signal_types = [
            ("hot_reason", "强势股题材归因"),
            ("northbound", "北向资金"),
            ("fund_flow", "个股资金流向"),
            ("dragon_tiger", "龙虎榜"),
            ("concept", "概念板块"),
            ("lockup", "限售解禁"),
        ]
        for st, label in signal_types:
            df = self.loader.read_signals(code, st, days=30)
            if not df.empty:
                signals[st] = df.to_dict("records")
        return signals

    # ============================
    # 缠论分析
    # ============================

    def _analyze_chanlun(self, kline: pd.DataFrame) -> dict:
        """缠论六步递归分解"""
        try:
            from chanlun.fractal import merge_klines, find_fractals
            from chanlun.pen import find_pens
            from chanlun.segment import find_segments
            from chanlun.central import find_centers
            from chanlun.signal import generate_signals

            merged = merge_klines(kline)
            fractals = find_fractals(merged)
            pens = find_pens(fractals)
            segments = find_segments(pens)
            centers = find_centers(segments)
            signals = generate_signals(centers)

            return {
                "fractals": len(fractals),
                "pens": len(pens),
                "segments": len(segments),
                "centers": len(centers),
                "signals": signals[:10] if signals else [],
                "direction": centers[-1].get("direction", "") if centers else "",
            }
        except Exception as e:
            logger.warning("缠论分析失败: %s", e)
            return {"error": str(e)}

    # ============================
    # 量化信号
    # ============================

    def _analyze_quantitative(self, kline: pd.DataFrame) -> dict:
        """量化策略信号"""
        try:
            from quantitative.strategy_base import StrategyEngine
            from quantitative.ma_strategy import MAStrategy
            from quantitative.momentum_strategy import MomentumStrategy

            engine = StrategyEngine()
            engine.add_strategy(MAStrategy())
            engine.add_strategy(MomentumStrategy())

            signals = engine.run_all(kline)
            return {
                "signals": signals[-10:] if len(signals) > 10 else signals,
                "total": len(signals),
                "latest": signals[-1] if signals else None,
            }
        except Exception as e:
            logger.warning("量化分析失败: %s", e)
            return {"error": str(e)}

    # ============================
    # 批量分析（多只股票）
    # ============================

    def analyze_batch(self, codes: List[str], days: int = 365,
                      parallel: bool = False) -> Dict[str, dict]:
        """批量分析多只股票"""
        results = {}
        for code in codes:
            try:
                results[code] = self.analyze_stock(code, days)
                logger.info("分析完成: %s", code)
            except Exception as e:
                logger.error("分析失败 [%s]: %s", code, e)
                results[code] = {"error": str(e)}
        return results

    # ============================
    # 排名/筛选
    # ============================

    def rank_stocks(self, metric: str = "change_pct", top_n: int = 20) -> List[dict]:
        """股票排名（按指定指标）"""
        all_stocks = self.loader.read_all_stocks()
        realtime_data = []
        for _, row in all_stocks.iterrows():
            code = row["stock_code"]
            rt = self.loader.read_realtime(code)
            if rt:
                realtime_data.append(rt)

        if not realtime_data:
            return []

        df = pd.DataFrame(realtime_data)
        sort_col = metric if metric in df.columns else "change_pct"
        df = df.sort_values(sort_col, ascending=False).head(top_n)
        return df.to_dict("records")

    def close(self):
        self.loader.close()


# ============================
# 便捷函数
# ============================

_engine = None


def get_engine() -> AnalysisEngine:
    global _engine
    if _engine is None:
        _engine = AnalysisEngine()
    return _engine


def analyze(code: str, days: int = 365) -> dict:
    """便捷函数：单股全量分析"""
    return get_engine().analyze_stock(code, days)


def rank(metric: str = "change_pct", top_n: int = 20) -> List[dict]:
    """便捷函数：股票排名"""
    return get_engine().rank_stocks(metric, top_n)
