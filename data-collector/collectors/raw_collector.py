"""
原始数据采集器 — 只负责采集原始数据，不做任何加工

职责边界:
  - 只做: HTTP/TCP 请求 → bytes → Kafka 消息
  - 不做: 数据解析、字段重命名、类型转换、清洗校验
  - 不做: 写入 MySQL、HDFS 或 CSV

数据流:
  RawCollector.fetch() → bytes → Kafka Topic
      ↓
  Spark Streaming 消费 → 解析 → MySQL(实时) + HDFS(备份)
"""

import json
import logging
import time
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("data_collector.raw")


class RawDataProducer(ABC):
    """原始数据生产者 — 只产出 bytes，不解析"""

    @abstractmethod
    def source_name(self) -> str:
        """数据源标识符"""
        ...

    @abstractmethod
    def fetch_raw(self, topic: str, params: dict = None) -> List[dict]:
        """采集原始数据，返回 [{topic, key, value_bytes, timestamp}, ...]

        value_bytes = 完整的 HTTP 响应体 / TCP 数据包的原始字节
        key        = 股票代码 / 基金代码 / 唯一标识
        topic      = Kafka topic 名称
        """
        ...


class TencentRawProducer(RawDataProducer):
    """腾讯财经 — 原始 HTTP 响应体"""

    def source_name(self) -> str:
        return "tencent"

    def fetch_raw(self, topic: str = "raw_realtime", params: dict = None) -> List[dict]:
        from collectors.stock_list import get_all_stock_codes
        codes = params.get("codes", get_all_stock_codes()) if params else get_all_stock_codes()
        prefixed = ",".join(
            f"{'sh' if c.startswith(('6','9')) else 'sz' if c.startswith(('0','3')) else 'bj'}{c}"
            for c in codes
        )
        url = f"https://qt.gtimg.cn/q={prefixed}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw_bytes = resp.read()  # GBK 编码原始字节
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


class MootdxRawProducer(RawDataProducer):
    """通达信 TCP — 原始二进制协议数据"""

    def source_name(self) -> str:
        return "mootdx"

    def fetch_raw(self, topic: str = "raw_kline", params: dict = None) -> List[dict]:
        try:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market='std')
        except ImportError:
            logger.warning("[mootdx] 未安装")
            return []

        code = (params or {}).get("code", "000001")
        try:
            klines = client.bars(symbol=code, category=4, offset=800)
            if klines is None:
                return []
            return [{
                "topic": topic,
                "key": code,
                "value": str(list(klines)),  # numpy 结构化数组 → str
                "source": self.source_name(),
                "fetch_time": datetime.now().isoformat(),
                "encoding": "binary",
            }]
        except Exception as e:
            logger.error("[mootdx] 原始采集失败: %s", e)
            return []


class RawDataCollector:
    """原始数据采集调度器 — 统一入口"""

    def __init__(self):
        self._producers: dict = {}
        self._kafka_enabled = False
        self._kafka_producer = None

    def register(self, producer: RawDataProducer):
        self._producers[producer.source_name()] = producer

    def _get_kafka_producer(self):
        if self._kafka_producer is None:
            try:
                from kafka import KafkaProducer
                from config import KAFKA_CONFIG
                kafka_cfg = KAFKA_CONFIG
                self._kafka_producer = KafkaProducer(
                    bootstrap_servers=kafka_cfg["bootstrap_servers"],
                    max_request_size=kafka_cfg["max_request_size"],
                    acks=kafka_cfg["acks"],
                    retries=kafka_cfg["retries"],
                )
                self._kafka_enabled = True
                logger.info("[Kafka] 生产者连接成功: %s", kafka_cfg["bootstrap_servers"])
            except Exception as e:
                logger.warning("[Kafka] 不可用，回退到本地文件: %s", e)
                self._kafka_enabled = False
        return self._kafka_producer

    def collect_and_publish(self, source: str, topic: str, params: dict = None) -> int:
        """采集原始数据并发布到 Kafka

        Returns: 发布的消息数
        """
        producer = self._producers.get(source)
        if not producer:
            logger.error("未知数据源: %s", source)
            return 0

        messages = producer.fetch_raw(topic, params)
        if not messages:
            return 0

        kafka = self._get_kafka_producer()
        published = 0

        for msg in messages:
            try:
                msg_bytes = json.dumps(msg, ensure_ascii=False).encode("utf-8")
                if kafka and self._kafka_enabled:
                    kafka.send(topic, key=msg["key"].encode(), value=msg_bytes)
                    published += 1
                else:
                    # Kafka 不可用时回退到本地文件
                    self._fallback_to_file(msg)
                    published += 1
            except Exception as e:
                logger.error("发布失败 [%s/%s]: %s", source, topic, e)

        if kafka and self._kafka_enabled:
            kafka.flush()

        logger.info("[%s] → %s: %d 条原始消息", source, topic, published)
        return published

    def _fallback_to_file(self, msg: dict):
        """Kafka 不可用时回退到本地 JSON 文件"""
        from pathlib import Path
        from config import DATA_DIR
        topic = msg.get("topic", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = DATA_DIR / f"raw_{topic}_{ts}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(msg, f, ensure_ascii=False)
        logger.info("[回退] → %s", fp.name)

    def close(self):
        if self._kafka_producer:
            self._kafka_producer.close()
