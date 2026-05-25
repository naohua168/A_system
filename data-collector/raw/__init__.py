"""
原始数据 Kafka 生产者模块 — 独立的生产者封装

职责:
  - 采集原始数据 → 序列化 → 发布到 Kafka Topic
  - Kafka 不可用时自动回退到本地 JSON 文件
  - 支持 10 个预定义 Topic (raw_realtime/raw_kline/raw_hot_reason 等)

数据流:
  RawKafkaProducer.produce(source, topic) → bytes → Kafka/文件
      ↓
  Spark Streaming 消费 → 解析 → MySQL(实时) + HDFS(备份)

用法:
    from raw.producer import RawKafkaProducer
    producer = RawKafkaProducer()
    producer.start()
    n = producer.collect_and_publish("tencent", "raw_realtime")
    report = producer.collect_all()
    producer.stop()
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("data_collector.raw.producer")

# ============================================================
# 配置（统一从 config.py 读取，提供独立默认值）
# ============================================================

try:
    from config import KAFKA_CONFIG, DATA_DIR, ENABLED_SOURCES
    _kafka_cfg = KAFKA_CONFIG
    _data_dir = DATA_DIR
    _enabled = ENABLED_SOURCES
except ImportError:
    _kafka_cfg = {
        "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "topics": {
            "realtime": "raw_realtime",
            "kline": "raw_kline",
            "fund_nav": "raw_fund_nav",
            "news": "raw_news",
            "filings": "raw_filings",
            "hot_reason": "raw_hot_reason",
            "northbound": "raw_northbound",
            "concept_blocks": "raw_concept_blocks",
            "fund_flow": "raw_fund_flow",
            "dragon_tiger": "raw_dragon_tiger",
        },
        "max_request_size": 10485760,
        "acks": "all",
        "retries": 3,
        "request_timeout_ms": 30000,
    }
    _data_dir = Path(os.getenv("OUTPUT_CSV_DIR", "./data/raw"))
    _data_dir.mkdir(parents=True, exist_ok=True)
    _enabled = {}


# ============================================================
# 消息模型
# ============================================================

class RawMessage:
    """原始数据消息 — 统一的 Kafka 消息结构"""

    def __init__(self, topic: str, key: str, value: str,
                 source: str, encoding: str = "utf-8",
                 **extra):
        self.topic = topic
        self.key = key
        self.value = value
        self.source = source
        self.encoding = encoding
        self.fetch_time = datetime.now().isoformat()
        self.extra = extra

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "fetch_time": self.fetch_time,
            "encoding": self.encoding,
            **self.extra,
        }

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict(), ensure_ascii=False).encode("utf-8")


# ============================================================
# Kafka 生产者封装
# ============================================================

class KafkaClient:
    """Kafka 客户端封装 — 懒加载 + 优雅回退"""

    def __init__(self, bootstrap_servers: str = None, config: dict = None):
        self._bootstrap = bootstrap_servers or _kafka_cfg["bootstrap_servers"]
        self._config = config or _kafka_cfg
        self._producer = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """连接 Kafka 集群（幂等，已连接则跳过）"""
        if self._connected and self._producer:
            return True
        try:
            from kafka import KafkaProducer
            self._producer = KafkaProducer(
                bootstrap_servers=self._bootstrap,
                max_request_size=self._config.get("max_request_size", 10485760),
                acks=self._config.get("acks", "all"),
                retries=self._config.get("retries", 3),
                request_timeout_ms=self._config.get("request_timeout_ms", 30000),
                compression_type="gzip",
            )
            self._connected = True
            logger.info("[KafkaClient] 连接成功: %s", self._bootstrap)
            return True
        except Exception as e:
            logger.warning("[KafkaClient] 连接失败，将使用本地回退: %s", e)
            self._connected = False
            self._producer = None
            return False

    def send(self, topic: str, key: str, value: bytes) -> bool:
        """发送单条消息到 Kafka"""
        if not self._connected and not self.connect():
            return False
        try:
            self._producer.send(
                topic,
                key=key.encode("utf-8") if isinstance(key, str) else key,
                value=value,
            )
            return True
        except Exception as e:
            logger.error("[KafkaClient] 发送失败 [%s/%s]: %s", topic, key, e)
            self._connected = False
            return False

    def flush(self, timeout: int = 10):
        """刷新所有缓冲消息"""
        if self._producer and self._connected:
            try:
                self._producer.flush(timeout=timeout)
            except Exception as e:
                logger.warning("[KafkaClient] flush 异常: %s", e)

    def close(self, timeout: int = 5):
        """关闭连接"""
        if self._producer:
            try:
                self._producer.close(timeout=timeout)
            except Exception as e:
                logger.warning("[KafkaClient] close 异常: %s", e)
        self._producer = None
        self._connected = False


# ============================================================
# 本地回退存储
# ============================================================

class FallbackStore:
    """Kafka 不可用时的本地文件回退存储"""

    def __init__(self, base_dir: Path = None):
        self._base_dir = base_dir or _data_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, topic: str, key: str, data: bytes) -> Path:
        """将消息保存到本地 JSON 文件"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        safe_key = "".join(c if c.isalnum() else "_" for c in str(key))[:20]
        filename = f"raw_{topic}_{safe_key}_{ts}.json"
        filepath = self._base_dir / filename
        try:
            with open(filepath, "wb") as f:
                f.write(data)
            logger.info("[Fallback] %s → %s (%d bytes)", topic, filename, len(data))
            return filepath
        except Exception as e:
            logger.error("[Fallback] 写入失败: %s", e)
            return None

    def list_files(self, topic: str = None) -> List[Path]:
        """列出已回退的文件"""
        pattern = f"raw_{topic}_*.json" if topic else "raw_*.json"
        return sorted(self._base_dir.glob(pattern))

    def get_stats(self) -> dict:
        """获取回退存储统计"""
        files = self.list_files()
        topics = set()
        total_size = 0
        for fp in files:
            parts = fp.stem.split("_")
            if len(parts) > 1:
                topics.add(parts[1])
            total_size += fp.stat().st_size
        return {
            "file_count": len(files),
            "topics": sorted(topics),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1048576, 2),
        }


# ============================================================
# 原始数据生产者 — 主入口
# ============================================================

TOPIC_MAP: Dict[str, str] = {
    "tencent": "raw_realtime",
    "mootdx": "raw_kline",
    "sina_kline": "raw_kline",
    "ths_hot": "raw_hot_reason",
    "ths_northbound": "raw_northbound",
    "baidu": "raw_concept_blocks",
    "akshare_ext": "raw_dragon_tiger",
    "information": "raw_news",
}


class RawKafkaProducer:
    """原始数据 Kafka 生产者 — 统一入口

    支持 3 种运行模式:
      1. Kafka 在线 — 实时发布
      2. Kafka 离线 — 本地 JSON 文件回退
      3. 仅同步 — 仅写入本地文件（可通过 sync_engine 后续导入 MySQL）

    用法:
        with RawKafkaProducer() as p:
            p.collect_and_publish("tencent")
            p.collect_all()
    """

    def __init__(self, max_workers: int = 4):
        self._kafka = KafkaClient()
        self._fallback = FallbackStore()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._started = False

    # -----------------------------------------------------------
    # 生命周期
    # -----------------------------------------------------------

    def start(self):
        """启动生产者 — 建立 Kafka 连接"""
        if self._started:
            return
        self._kafka.connect()
        self._started = True
        logger.info("[RawKafkaProducer] 启动完成, Kafka=%s",
                     "在线" if self._kafka.is_connected else "离线(回退模式)")

    def stop(self):
        """停止生产者 — 刷新缓冲区并关闭连接"""
        if self._kafka.is_connected:
            self._kafka.flush()
        self._kafka.close()
        self._executor.shutdown(wait=False)
        self._started = False
        logger.info("[RawKafkaProducer] 已停止")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    # -----------------------------------------------------------
    # 发布核心
    # -----------------------------------------------------------

    def publish(self, msg: RawMessage) -> bool:
        """发布一条消息到 Kafka（回退时写入本地文件）"""
        data = msg.to_json()

        if self._kafka.is_connected:
            ok = self._kafka.send(msg.topic, msg.key, data)
            if ok:
                return True

        # Kafka 不可用 → 回退到本地文件
        self._fallback.save(msg.topic, msg.key, data)
        return True

    def publish_batch(self, messages: List[RawMessage]) -> int:
        """批量发布消息"""
        count = 0
        for msg in messages:
            if self.publish(msg):
                count += 1

        if self._kafka.is_connected:
            self._kafka.flush()

        return count

    # -----------------------------------------------------------
    # 采集 + 发布（调用现有 raw_collector.py）
    # -----------------------------------------------------------

    def collect_and_publish(self, source: str, topic: str = None,
                            params: dict = None) -> int:
        """从指定数据源采集原始数据并发布

        Args:
            source: 数据源标识 (tencent/mootdx/ths_hot/...)
            topic: 目标 Kafka Topic，None 时使用默认映射
            params: 采集参数

        Returns:
            成功发布的消息数
        """
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        collector.register_all()
        return collector.collect_and_publish(source, topic, params)

    def collect_all(self, params_overrides: dict = None) -> Dict[str, int]:
        """采集所有已启用数据源的原始数据

        Returns:
            {source_name: published_count}
        """
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        collector.register_all()
        return collector.collect_all(params_overrides)

    # -----------------------------------------------------------
    # 并发采集
    # -----------------------------------------------------------

    def collect_concurrent(self, sources: List[str] = None,
                           max_workers: int = 4) -> Dict[str, int]:
        """并发采集多个数据源

        Args:
            sources: 要采集的数据源列表，None 表示全部
            max_workers: 最大并发数

        Returns:
            {source_name: published_count}
        """
        if sources is None:
            sources = list(TOPIC_MAP.keys())

        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            fut_map = {
                executor.submit(self.collect_and_publish, src, TOPIC_MAP.get(src)): src
                for src in sources
            }
            for fut in as_completed(fut_map):
                src = fut_map[fut]
                try:
                    results[src] = fut.result()
                except Exception as e:
                    logger.error("[并发] %s 采集失败: %s", src, e)
                    results[src] = -1

        return results

    # -----------------------------------------------------------
    # 健康检查
    # -----------------------------------------------------------

    def health_check(self) -> dict:
        """检查 Kafka 及各数据源健康状态"""
        status = {"kafka": self._kafka.is_connected, "sources": {}}

        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        collector.register_all()
        status["sources"] = collector.health_check()

        return status

    # -----------------------------------------------------------
    # 工具方法
    # -----------------------------------------------------------

    def list_topics(self) -> List[str]:
        """返回所有可用 Topic 列表"""
        return sorted(set(_kafka_cfg.get("topics", {}).values()))

    def get_fallback_stats(self) -> dict:
        """获取本地回退存储统计"""
        return self._fallback.get_stats()
