"""
原始数据采集器 — 只负责采集原始数据，不做任何加工

职责边界:
  - 只做: HTTP/TCP 请求 → bytes → Kafka 消息
  - 不做: 数据解析、字段重命名、类型转换、清洗校验
  - 不做: 写入 MySQL、HDFS 或 CSV

数据流:
  RawDataCollector.collect_and_publish(source, topic) → bytes → Kafka Topic
      ↓
  Spark Streaming 消费 → 解析 → MySQL(实时) + HDFS(备份)

已覆盖数据源:
  1. tencent       — 腾讯财经 HTTP 原始响应体（实时行情/PE/PB/市值）
  2. mootdx        — 通达信 TCP 二进制协议（K线/Socket5快照）
  3. ths_hot       — 同花顺强势股题材归因 JSON 响应
  4. ths_northbound — 同花顺北向资金实时分钟流向 JSON
  5. baidu         — 百度股市通 PAE 协议（概念板块+资金流向）
  6. akshare_ext   — akshare 扩展（龙虎榜/解禁/行业对比）
  7. information   — 资讯层原始数据（研报/新闻/公告/一致预期/财联社/全球资讯）
  8. sina_kline    — 新浪财经 HTTP K线原始响应
"""

import json
import logging
import time
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("data_collector.raw")


# ============================================================
# 抽象基类
# ============================================================

class RawDataProducer(ABC):
    """原始数据生产者 — 只产出 bytes 或字符串，不做领域解析"""

    @abstractmethod
    def source_name(self) -> str:
        """数据源标识符"""
        ...

    @abstractmethod
    def fetch_raw(self, topic: str, params: dict = None) -> List[dict]:
        """采集原始数据，返回 [message_dict, ...]

        每个 message_dict 字段说明:
          topic      — Kafka topic 名称
          key        — 股票代码/基金代码/批次标识
          value      — 原始响应体（字符串或 bytes 序列化后的字符串）
          source     — 数据源标识
          fetch_time — ISO 格式采集时间戳
          encoding   — 原始编码标识
        """
        ...

    def health_check(self) -> bool:
        """子类可覆盖的轻量健康检查，默认尝试 fetch_raw 一次"""
        try:
            result = self.fetch_raw("health_check", {"codes": ["000001"]})
            return len(result) > 0
        except Exception:
            return False


# ============================================================
# 腾讯财经 — 原始 HTTP 响应体
# ============================================================

class TencentRawProducer(RawDataProducer):
    """腾讯财经 — 批量查询实时行情的原始 HTTP 响应体（GBK 编码）"""

    def source_name(self) -> str:
        return "tencent"

    def fetch_raw(self, topic: str = "raw_realtime", params: dict = None) -> List[dict]:
        from collectors.stock_list import get_all_stock_codes
        codes = (params or {}).get("codes", get_all_stock_codes())
        prefixed = ",".join(
            f"{'sh' if c.startswith(('6','9')) else 'sz' if c.startswith(('0','3')) else 'bj'}{c}"
            for c in codes
        )
        url = f"https://qt.gtimg.cn/q={prefixed}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw_bytes = resp.read()
            return [{
                "topic": topic,
                "key": "batch",
                "value": raw_bytes.decode("gbk", errors="replace"),
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "gbk",
            }]
        except Exception as e:
            logger.error("[tencent] 原始采集失败: %s", e)
            return []


# ============================================================
# 通达信 TCP — 原始二进制协议数据
# ============================================================

class MootdxRawProducer(RawDataProducer):
    """通达信 TCP — mootdx 库封装的原始二进制行情数据"""

    def source_name(self) -> str:
        return "mootdx"

    def fetch_raw(self, topic: str = "raw_kline", params: dict = None) -> List[dict]:
        try:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market='std')
        except ImportError:
            logger.warning("[mootdx] 未安装")
            return []

        params = params or {}
        codes = params.get("codes", ["000001"])
        results = []

        for code in codes:
            try:
                klines = client.bars(symbol=code, category=4, offset=800)
                if klines is not None:
                    results.append({
                        "topic": topic,
                        "key": code,
                        "value": str(list(klines)),
                        "source": self.source_name(),
                        "fetch_time": datetime.now().isoformat(),
                        "encoding": "binary",
                    })
                # 限流，防止 TCP 连接风暴
                time.sleep(0.1)
            except Exception as e:
                logger.error("[mootdx] %s 原始采集失败: %s", code, e)

        return results


# ============================================================
# 同花顺强势股题材归因 — 原始 JSON 响应
# ============================================================

class ThsHotRawProducer(RawDataProducer):
    """同花顺热点 — 当日强势股+题材归因的原始 JSON 响应"""

    def source_name(self) -> str:
        return "ths_hot"

    def fetch_raw(self, topic: str = "raw_hot_reason", params: dict = None) -> List[dict]:
        from collectors.ths_hot_collector import ThsHotCollector
        collector = ThsHotCollector()
        try:
            # 直接采集原始数据，不经过 DataFrame 加工
            import requests
            date_str = (params or {}).get("date_str")
            # 使用同花顺热点 API 的原始 URL
            url = (
                f"https://push2.eastmoney.com/api/qt/clist/get"
                f"?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                f"&fltt=2&invt=2&fid=f3&fs=m:90+t:3+f:!50&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13"
            )
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://data.eastmoney.com/",
            }, timeout=15)

            entry = {
                "topic": topic,
                "key": "hot_reason",
                "value": resp.text,
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "utf-8",
                "original_url": url,
            }
            return [entry]
        except Exception as e:
            logger.error("[ths_hot] 原始采集失败: %s", e)
            return []


# ============================================================
# 同花顺北向资金 — 原始 JSON 响应
# ============================================================

class ThsNorthboundRawProducer(RawDataProducer):
    """同花顺北向资金 — 实时分钟流向的原始 JSON 响应"""

    def source_name(self) -> str:
        return "ths_northbound"

    def fetch_raw(self, topic: str = "raw_northbound", params: dict = None) -> List[dict]:
        import requests
        try:
            url = (
                "https://push2.eastmoney.com/api/qt/kamt.kline/get"
                "?fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55"
                "&klt=1&lmt=262&secid=1.000001"
            )
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://data.eastmoney.com/",
            }, timeout=15)

            entry = {
                "topic": topic,
                "key": "northbound",
                "value": resp.text,
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "utf-8",
                "original_url": url,
            }
            return [entry]
        except Exception as e:
            logger.error("[ths_northbound] 原始采集失败: %s", e)
            return []


# ============================================================
# 百度股市通 — PAE 协议原始响应
# ============================================================

class BaiduRawProducer(RawDataProducer):
    """百度股市通 — 概念板块+资金流量的原始 PAE 响应"""

    def source_name(self) -> str:
        return "baidu"

    def fetch_raw(self, topic: str = "raw_concept_blocks", params: dict = None) -> List[dict]:
        import requests
        params = params or {}
        code = params.get("code", "000001")
        focus = params.get("focus", "concept")
        results = []

        topics_map = {
            "concept": "raw_concept_blocks",
            "fund": "raw_fund_flow",
        }
        actual_topic = topics_map.get(focus, topic)

        try:
            # 使用百度 PAE 协议原始端点
            url = f"https://gou20.baidu.com/api/stock/cai?code={code}&stockType=stock"
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; BaiduStockBot/1.0)",
                "Referer": "https://gushitong.baidu.com/",
            }, timeout=15)

            results.append({
                "topic": actual_topic,
                "key": code,
                "value": resp.text,
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "utf-8",
                "original_url": url,
            })
        except Exception as e:
            logger.error("[baidu] %s 原始采集失败: %s", code, e)

        return results


# ============================================================
# akshare 扩展 — 原始 JSON 数据
# ============================================================

class AkshareExtRawProducer(RawDataProducer):
    """akshare 扩展 — 龙虎榜/解禁/行业对比的原始数据"""

    def source_name(self) -> str:
        return "akshare_ext"

    def fetch_raw(self, topic: str = "raw_dragon_tiger", params: dict = None) -> List[dict]:
        import requests
        params = params or {}
        focus = params.get("focus", "dragon_tiger")
        results = []

        # 可直接访问的原始 API 端点（不依赖 akshare 库）
        try:
            if focus == "dragon_tiger":
                trade_date = params.get("date_str", datetime.now().strftime("%Y-%m-%d"))
                url = (
                    f"https://push2.eastmoney.com/api/qt/clist/get"
                    f"?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                    f"&fltt=2&invt=2&fid=f3&fs=m:90+t:1+f:!50"
                    f"&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124"
                )
                key = f"dragon_tiger_{trade_date}"
            elif focus == "industry":
                url = (
                    "https://push2.eastmoney.com/api/qt/clist/get"
                    "?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                    "&fltt=2&invt=2&fid=f3&fs=m:90+t:2"
                    "&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124"
                )
                key = "industry_compare"
            else:
                code = params.get("code", "000001")
                url = (
                    f"https://push2.eastmoney.com/api/qt/clist/get"
                    f"?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
                    f"&fltt=2&invt=2&fid=f3&fs=m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2"
                    f"&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72"
                )
                key = f"lockup_{code}"

            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://data.eastmoney.com/",
            }, timeout=15)

            results.append({
                "topic": topic,
                "key": key,
                "value": resp.text,
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "utf-8",
                "original_url": url,
            })
        except Exception as e:
            logger.error("[akshare_ext] %s 原始采集失败: %s", focus, e)

        return results


# ============================================================
# 资讯层 — 原始数据（研报/新闻/公告/一致预期/财联社/全球资讯）
# ============================================================

class InformationRawProducer(RawDataProducer):
    """资讯层 — 研报/新闻/公告/一致预期/财联社/全球资讯的原始数据"""

    def source_name(self) -> str:
        return "information"

    def fetch_raw(self, topic: str = "raw_news", params: dict = None) -> List[dict]:
        import requests
        params = params or {}
        focus = params.get("focus", "cls_news")
        results = []

        try:
            if focus == "cls_news":
                url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.0.8"
                payload = {"type": "telegram", "limit": 50}
                resp = requests.post(url, json=payload, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                }, timeout=15)
                key = "cls_news"
            elif focus == "global_news":
                url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.0.8"
                payload = {"type": "global", "limit": 50}
                resp = requests.post(url, json=payload, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                }, timeout=15)
                key = "global_news"
            elif focus == "research":
                code = params.get("code", "")
                url = (
                    f"https://reportapi.eastmoney.com/report/list"
                    f"?cb=&stockCode={code}&pageSize=50&pageNum=1"
                    f"&industryCode=*&industry=*&rating=*&ratingChange=*"
                    f"&beginTime=&endTime=&fields=&sortType=1&reportDateType=0"
                    f"&pageNo=1"
                )
                resp = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://data.eastmoney.com/",
                }, timeout=15)
                key = f"research_{code}"
            elif focus == "filings":
                code = params.get("code", "")
                url = (
                    f"https://np-anotice-stock.eastmoney.com/api/security/announcement/"
                    f"getannouncement?pageSize=50&pageNum=1&stock_list={code}"
                    f"&f_node=0&s_node=0&begin_time=&end_time=&noticesrctype=all"
                )
                resp = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://data.eastmoney.com/",
                }, timeout=15)
                key = f"filings_{code}"
            else:
                logger.warning("[information] 未知 focus: %s", focus)
                return []

            results.append({
                "topic": topic,
                "key": key,
                "value": resp.text,
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "utf-8",
                "original_url": url,
            })
        except Exception as e:
            logger.error("[information] %s 原始采集失败: %s", focus, e)

        return results


# ============================================================
# 新浪财经 K 线 — 原始 HTTP 响应
# ============================================================

class SinaKlineRawProducer(RawDataProducer):
    """新浪财经 — 日 K 线原始 HTTP CSV 响应"""

    def source_name(self) -> str:
        return "sina_kline"

    def fetch_raw(self, topic: str = "raw_kline", params: dict = None) -> List[dict]:
        import requests
        params = params or {}
        codes = params.get("codes", ["000001"])
        freq = params.get("freq", "daily")
        days = params.get("days", 365)
        results = []

        # freq 映射到新浪 K 线周期参数
        scale_map = {"daily": 64, "weekly": 128, "monthly": 320}
        scale = scale_map.get(freq, 64)
        datalen = days

        for code in codes:
            try:
                # 新浪 K 线原始 CSV 端点
                url = (
                    f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                    f"CN_MarketData.getKLineData?symbol={code}&scale={scale}&ma=5&datalen={datalen}"
                )
                resp = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0",
                }, timeout=15)

                results.append({
                    "topic": topic,
                    "key": code,
                    "value": resp.text,
                    "source": self.source_name(),
                    "fetch_time": datetime.now().isoformat(),
                    "encoding": "utf-8",
                    "freq": freq,
                    "original_url": url,
                })
                time.sleep(0.3)  # 防反爬限流
            except Exception as e:
                logger.error("[sina_kline] %s 原始采集失败: %s", code, e)

        return results


# ============================================================
# 生产者注册表 & 自动注册
# ============================================================

_PRODUCER_REGISTRY: Dict[str, type] = {
    "tencent": TencentRawProducer,
    "mootdx": MootdxRawProducer,
    "ths_hot": ThsHotRawProducer,
    "ths_northbound": ThsNorthboundRawProducer,
    "baidu": BaiduRawProducer,
    "akshare_ext": AkshareExtRawProducer,
    "information": InformationRawProducer,
    "sina_kline": SinaKlineRawProducer,
}

_TOPIC_MAP: Dict[str, str] = {
    "tencent": "raw_realtime",
    "mootdx": "raw_kline",
    "sina_kline": "raw_kline",
    "ths_hot": "raw_hot_reason",
    "ths_northbound": "raw_northbound",
    "baidu": "raw_concept_blocks",
    "akshare_ext": "raw_dragon_tiger",
    "information": "raw_news",
}


def register_producers(collector: "RawDataCollector"):
    """注册所有可用的原始数据生产者"""
    for name, cls in _PRODUCER_REGISTRY.items():
        from config import ENABLED_SOURCES
        if ENABLED_SOURCES.get(name, True):
            collector.register(cls())
            logger.debug("[raw] 注册生产者: %s", name)


# ============================================================
# 原始数据采集调度器 — 增强版
# ============================================================

class RawDataCollector:
    """原始数据采集调度器 — 统一入口

    用法:
        collector = RawDataCollector()
        collector.register_all()

        # 单源采集
        n = collector.collect_and_publish("tencent", "raw_realtime")

        # 批量采集
        report = collector.collect_all()

        # 按层采集
        report = collector.collect_layer("market")
    """

    def __init__(self):
        self._producers: Dict[str, RawDataProducer] = {}
        self._kafka_enabled = False
        self._kafka_producer = None

    # -----------------------------------------------------------
    # 注册管理
    # -----------------------------------------------------------

    def register(self, producer: RawDataProducer):
        """注册一个原始数据生产者"""
        self._producers[producer.source_name()] = producer

    def register_all(self):
        """注册所有可用的原始数据生产者"""
        register_producers(self)

    def list_producers(self) -> List[str]:
        """列出所有已注册的生产者"""
        return list(self._producers.keys())

    def get_producer(self, source: str) -> Optional[RawDataProducer]:
        """获取指定数据源的生产者"""
        return self._producers.get(source)

    # -----------------------------------------------------------
    # Kafka 连接管理
    # -----------------------------------------------------------

    def _get_kafka_producer(self):
        """获取 Kafka 生产者（懒加载 + 自动回退）"""
        if self._kafka_producer is None:
            try:
                from kafka import KafkaProducer
                from config import KAFKA_CONFIG

                kafka_cfg = KAFKA_CONFIG
                self._kafka_producer = KafkaProducer(
                    bootstrap_servers=kafka_cfg["bootstrap_servers"],
                    max_request_size=kafka_cfg.get("max_request_size", 10485760),
                    acks=kafka_cfg.get("acks", "all"),
                    retries=kafka_cfg.get("retries", 3),
                    request_timeout_ms=kafka_cfg.get("request_timeout_ms", 30000),
                )
                self._kafka_enabled = True
                logger.info("[Kafka] 生产者连接成功: %s", kafka_cfg["bootstrap_servers"])
            except Exception as e:
                logger.warning("[Kafka] 不可用，回退到本地文件: %s", e)
                self._kafka_enabled = False
        return self._kafka_producer

    @property
    def kafka_connected(self) -> bool:
        """Kafka 是否已连接"""
        return self._kafka_enabled

    # -----------------------------------------------------------
    # 核心：单源采集与发布
    # -----------------------------------------------------------

    def collect_and_publish(self, source: str, topic: str = None,
                            params: dict = None) -> int:
        """采集原始数据并发布到 Kafka/本地文件

        Args:
            source: 数据源标识（tencent / mootdx / ...）
            topic:  Kafka topic，None 时使用默认 topic
            params: 采集参数（codes、focus 等）

        Returns:
            成功发布的消息数
        """
        producer = self._producers.get(source)
        if not producer:
            logger.error("[raw] 未知数据源: %s，可用: %s", source, list(self._producers.keys()))
            return 0

        # 使用默认 topic（如果未指定）
        if topic is None:
            topic = _TOPIC_MAP.get(source, f"raw_{source}")

        params = params or {}
        try:
            messages = producer.fetch_raw(topic, params)
        except Exception as e:
            logger.error("[raw] %s fetch_raw 异常: %s", source, e)
            return 0

        if not messages:
            logger.info("[raw] %s 无原始消息产出", source)
            return 0

        kafka = self._get_kafka_producer()
        published = 0

        for msg in messages:
            try:
                msg_bytes = json.dumps(msg, ensure_ascii=False).encode("utf-8")
                if kafka and self._kafka_enabled:
                    kafka.send(topic, key=str(msg.get("key", "")).encode(), value=msg_bytes)
                    published += 1
                else:
                    self._fallback_to_file(msg)
                    published += 1
            except Exception as e:
                logger.error("[raw] 发布失败 [%s/%s]: %s", source, topic, e)

        if kafka and self._kafka_enabled:
            try:
                kafka.flush()
            except Exception as e:
                logger.warning("[raw] Kafka flush 异常: %s", e)

        logger.info("[raw] %s → %s: %d 条原始消息", source, topic, published)
        return published

    # -----------------------------------------------------------
    # 批量采集
    # -----------------------------------------------------------

    def collect_all(self, params_overrides: dict = None) -> Dict[str, int]:
        """采集所有已注册数据源的原始数据

        Returns:
            {source: published_count}
        """
        results = {}
        params_overrides = params_overrides or {}

        for source in self._producers:
            topic = _TOPIC_MAP.get(source, f"raw_{source}")
            params = params_overrides.get(source, {})
            try:
                count = self.collect_and_publish(source, topic, params)
                results[source] = count
            except Exception as e:
                logger.error("[raw] collect_all %s 失败: %s", source, e)
                results[source] = -1

        logger.info("[raw] collect_all 完成: %s", results)
        return results

    def collect_sources(self, sources: List[str], topic: str = None,
                         params: dict = None) -> Dict[str, int]:
        """采集指定的多个数据源"""
        results = {}
        for source in sources:
            results[source] = self.collect_and_publish(source, topic, params)
        return results

    # -----------------------------------------------------------
    # 健康检查
    # -----------------------------------------------------------

    def health_check(self) -> Dict[str, dict]:
        """检查所有已注册数据源的健康状态

        Returns:
            {source: {"available": bool, "error": str}}
        """
        status = {}
        for name, producer in self._producers.items():
            info = {"available": False, "error": ""}
            try:
                info["available"] = producer.health_check()
            except Exception as e:
                info["error"] = str(e)[:100]
            status[name] = info
        return status

    # -----------------------------------------------------------
    # Kafka 回退
    # -----------------------------------------------------------

    def _fallback_to_file(self, msg: dict):
        """Kafka 不可用时回退到本地 JSON 文件"""
        from pathlib import Path
        from config import DATA_DIR
        topic = msg.get("topic", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = DATA_DIR / f"raw_{topic}_{ts}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(msg, f, ensure_ascii=False)
        logger.info("[raw 回退] → %s", fp.name)

    # -----------------------------------------------------------
    # 生命周期
    # -----------------------------------------------------------

    def close(self):
        """关闭 Kafka 生产者连接"""
        if self._kafka_producer:
            try:
                self._kafka_producer.close(timeout=5)
            except Exception as e:
                logger.warning("[raw] Kafka close 异常: %s", e)
            self._kafka_producer = None
            self._kafka_enabled = False
