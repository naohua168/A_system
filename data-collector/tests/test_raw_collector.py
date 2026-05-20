"""
原始数据采集器单元测试（全 mock，不依赖网络/MySQL/Kafka）
覆盖 RealDataProducer 基类 + 8 个生产者 + RawDataCollector 全部方法
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


# ============================================================
# 测试 RawDataProducer 抽象基类行为
# ============================================================

class TestRawDataProducerBase:
    """测试 RawDataProducer 抽象基类"""

    def test_cannot_instantiate_abstract(self):
        """验证抽象基类不可直接实例化"""
        from collectors.raw_collector import RawDataProducer
        with pytest.raises(TypeError):
            RawDataProducer()

    def test_health_check_default_returns_false_on_exception(self):
        """测试 health_check 默认实现在异常时返回 False"""
        from collectors.raw_collector import RawDataProducer

        class BadProducer(RawDataProducer):
            def source_name(self):
                return "bad"

            def fetch_raw(self, topic, params=None):
                raise RuntimeError("network error")

        producer = BadProducer()
        assert not producer.health_check()

    def test_producer_creates_messages_with_required_fields(self):
        """验证 fetch_raw 返回的每条消息都包含必要字段"""
        from collectors.raw_collector import TencentRawProducer

        producer = TencentRawProducer()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"v_a=10.0"
            mock_urlopen.return_value = mock_resp

            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001"]):
                messages = producer.fetch_raw("raw_realtime")

        assert len(messages) == 1
        msg = messages[0]
        assert "topic" in msg
        assert "key" in msg
        assert "value" in msg
        assert "source" in msg
        assert "fetch_time" in msg
        assert "encoding" in msg
        assert msg["topic"] == "raw_realtime"
        assert msg["source"] == "tencent"


# ============================================================
# 测试 TencentRawProducer
# ============================================================

class TestTencentRawProducer:
    """腾讯财经原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import TencentRawProducer
        assert TencentRawProducer().source_name() == "tencent"

    def test_fetch_raw_success(self):
        from collectors.raw_collector import TencentRawProducer
        producer = TencentRawProducer()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"v_a=10.0"
            mock_urlopen.return_value = mock_resp

            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001", "600519"]):
                messages = producer.fetch_raw("raw_realtime")

        assert len(messages) == 1
        assert messages[0]["key"] == "batch"
        assert "v_a=10.0" in messages[0]["value"]
        assert messages[0]["encoding"] == "gbk"

    def test_fetch_raw_network_error(self):
        from collectors.raw_collector import TencentRawProducer
        producer = TencentRawProducer()

        with patch("urllib.request.urlopen", side_effect=ConnectionError("timeout")):
            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001"]):
                messages = producer.fetch_raw("raw_realtime")

        assert messages == []

    def test_fetch_raw_with_custom_codes(self):
        from collectors.raw_collector import TencentRawProducer
        producer = TencentRawProducer()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"mock_data"
            mock_urlopen.return_value = mock_resp

            messages = producer.fetch_raw("raw_realtime", {"codes": ["000001"]})

        assert len(messages) == 1
        # 验证使用了自定义 codes，不调用 get_all_stock_codes
        req_url = mock_urlopen.call_args[0][0].full_url
        assert "sz000001" in req_url

    def test_health_check(self):
        from collectors.raw_collector import TencentRawProducer
        producer = TencentRawProducer()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"ok"
            mock_urlopen.return_value = mock_resp

            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001"]):
                assert producer.health_check()


# ============================================================
# 测试 MootdxRawProducer
# ============================================================

class TestMootdxRawProducer:
    """通达信 TCP 原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import MootdxRawProducer
        assert MootdxRawProducer().source_name() == "mootdx"

    def test_fetch_raw_no_mootdx(self):
        """mootdx 未安装时返回空"""
        from collectors.raw_collector import MootdxRawProducer
        producer = MootdxRawProducer()

        with patch.dict("sys.modules", {"mootdx": None}):
            with patch("builtins.__import__", side_effect=ImportError("no mootdx")):
                messages = producer.fetch_raw("raw_kline")

        assert messages == []

    def test_fetch_raw_success(self):
        from collectors.raw_collector import MootdxRawProducer
        import numpy as np

        producer = MootdxRawProducer()

        mock_klines = np.array(
            [(20250101, 10.0, 10.5, 9.8, 10.2, 1000000)],
            dtype=[("date", int), ("open", float), ("high", float),
                   ("low", float), ("close", float), ("volume", int)],
        )

        mock_client = MagicMock()
        mock_client.bars.return_value = mock_klines

        with patch("mootdx.quotes.Quotes.factory", return_value=mock_client):
            messages = producer.fetch_raw("raw_kline", {"codes": ["000001"]})

        assert len(messages) == 1
        assert messages[0]["key"] == "000001"
        assert messages[0]["encoding"] == "binary"
        assert messages[0]["source"] == "mootdx"

    def test_fetch_raw_bars_none(self):
        from collectors.raw_collector import MootdxRawProducer

        producer = MootdxRawProducer()
        mock_client = MagicMock()
        mock_client.bars.return_value = None

        with patch("mootdx.quotes.Quotes.factory", return_value=mock_client):
            messages = producer.fetch_raw("raw_kline", {"codes": ["000001"]})

        assert len(messages) == 0


# ============================================================
# 测试 ThsHotRawProducer
# ============================================================

class TestThsHotRawProducer:
    """同花顺热点原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import ThsHotRawProducer
        assert ThsHotRawProducer().source_name() == "ths_hot"

    def test_fetch_raw_success(self):
        from collectors.raw_collector import ThsHotRawProducer
        producer = ThsHotRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":{"total":50,"diff":[{"f12":"000001"}]}}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_hot_reason")

        assert len(messages) == 1
        assert messages[0]["key"] == "hot_reason"
        assert messages[0]["encoding"] == "utf-8"
        assert "000001" in messages[0]["value"]

    def test_fetch_raw_failure(self):
        from collectors.raw_collector import ThsHotRawProducer
        producer = ThsHotRawProducer()

        with patch("requests.get", side_effect=ConnectionError("timeout")):
            messages = producer.fetch_raw("raw_hot_reason")

        assert messages == []


# ============================================================
# 测试 ThsNorthboundRawProducer
# ============================================================

class TestThsNorthboundRawProducer:
    """同花顺北向资金原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import ThsNorthboundRawProducer
        assert ThsNorthboundRawProducer().source_name() == "ths_northbound"

    def test_fetch_raw_success(self):
        from collectors.raw_collector import ThsNorthboundRawProducer
        producer = ThsNorthboundRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":{"klines":["2025-01-01,10.0,5.0"]}}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_northbound")

        assert len(messages) == 1
        assert messages[0]["key"] == "northbound"

    def test_fetch_raw_failure(self):
        from collectors.raw_collector import ThsNorthboundRawProducer
        producer = ThsNorthboundRawProducer()

        with patch("requests.get", side_effect=ConnectionError("timeout")):
            messages = producer.fetch_raw("raw_northbound")
        assert messages == []


# ============================================================
# 测试 BaiduRawProducer
# ============================================================

class TestBaiduRawProducer:
    """百度股市通原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import BaiduRawProducer
        assert BaiduRawProducer().source_name() == "baidu"

    def test_fetch_raw_concept(self):
        from collectors.raw_collector import BaiduRawProducer
        producer = BaiduRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"concept_tags":["人工智能"]}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_concept_blocks",
                                          {"code": "000001", "focus": "concept"})

        assert len(messages) == 1
        assert messages[0]["key"] == "000001"

    def test_fetch_raw_failure(self):
        from collectors.raw_collector import BaiduRawProducer
        producer = BaiduRawProducer()

        with patch("requests.get", side_effect=ConnectionError("timeout")):
            messages = producer.fetch_raw("raw_concept_blocks",
                                          {"code": "000001", "focus": "concept"})
        assert messages == []


# ============================================================
# 测试 AkshareExtRawProducer
# ============================================================

class TestAkshareExtRawProducer:
    """akshare 扩展原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import AkshareExtRawProducer
        assert AkshareExtRawProducer().source_name() == "akshare_ext"

    def test_fetch_raw_dragon_tiger(self):
        from collectors.raw_collector import AkshareExtRawProducer
        producer = AkshareExtRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":{"diff":[{"f12":"000001"}]}}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_dragon_tiger",
                                          {"focus": "dragon_tiger"})

        assert len(messages) == 1
        assert "dragon_tiger" in messages[0]["key"]

    def test_fetch_raw_industry(self):
        from collectors.raw_collector import AkshareExtRawProducer
        producer = AkshareExtRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":{"diff":[{"f12":"银行"}]}}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_signal",
                                          {"focus": "industry"})

        assert len(messages) == 1
        assert messages[0]["key"] == "industry_compare"

    def test_fetch_raw_failure(self):
        from collectors.raw_collector import AkshareExtRawProducer
        producer = AkshareExtRawProducer()

        with patch("requests.get", side_effect=ConnectionError("timeout")):
            messages = producer.fetch_raw("raw_dragon_tiger",
                                          {"focus": "dragon_tiger"})
        assert messages == []


# ============================================================
# 测试 InformationRawProducer
# ============================================================

class TestInformationRawProducer:
    """资讯层原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import InformationRawProducer
        assert InformationRawProducer().source_name() == "information"

    def test_fetch_raw_cls_news(self):
        from collectors.raw_collector import InformationRawProducer
        producer = InformationRawProducer()

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":[{"id":123,"title":"test"}]}'
            mock_post.return_value = mock_resp

            messages = producer.fetch_raw("raw_news", {"focus": "cls_news"})

        assert len(messages) == 1
        assert messages[0]["key"] == "cls_news"

    def test_fetch_raw_global_news(self):
        from collectors.raw_collector import InformationRawProducer
        producer = InformationRawProducer()

        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":[{"id":456,"title":"global"}]}'
            mock_post.return_value = mock_resp

            messages = producer.fetch_raw("raw_news", {"focus": "global_news"})

        assert len(messages) == 1
        assert messages[0]["key"] == "global_news"

    def test_fetch_raw_research(self):
        from collectors.raw_collector import InformationRawProducer
        producer = InformationRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":[{"stockCode":"000001"}]}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_news",
                                          {"focus": "research", "code": "000001"})

        assert len(messages) == 1
        assert "research" in messages[0]["key"]

    def test_fetch_raw_filings(self):
        from collectors.raw_collector import InformationRawProducer
        producer = InformationRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":[{"announcementTitle":"test"}]}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_news",
                                          {"focus": "filings", "code": "000001"})

        assert len(messages) == 1
        assert "filings" in messages[0]["key"]

    def test_fetch_raw_unknown_focus(self):
        from collectors.raw_collector import InformationRawProducer
        producer = InformationRawProducer()

        messages = producer.fetch_raw("raw_news", {"focus": "unknown_type"})

        assert messages == []

    def test_fetch_raw_failure(self):
        from collectors.raw_collector import InformationRawProducer
        producer = InformationRawProducer()

        with patch("requests.post", side_effect=ConnectionError("timeout")):
            messages = producer.fetch_raw("raw_news", {"focus": "cls_news"})
        assert messages == []


# ============================================================
# 测试 SinaKlineRawProducer
# ============================================================

class TestSinaKlineRawProducer:
    """新浪 K 线原始数据生产者测试"""

    def test_source_name(self):
        from collectors.raw_collector import SinaKlineRawProducer
        assert SinaKlineRawProducer().source_name() == "sina_kline"

    def test_fetch_raw_success(self):
        from collectors.raw_collector import SinaKlineRawProducer
        producer = SinaKlineRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '{"data":[{"day":"2025-01-01","open":"10.0"}]}'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_kline", {"codes": ["000001"]})

        assert len(messages) == 1
        assert messages[0]["key"] == "000001"
        assert messages[0]["freq"] == "daily"

    def test_fetch_raw_with_freq_params(self):
        from collectors.raw_collector import SinaKlineRawProducer
        producer = SinaKlineRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '[{"day":"2025-01-01"}]'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_kline", {
                "codes": ["000001"], "freq": "weekly", "days": 100,
            })

        assert len(messages) == 1
        # 验证 URL 中包含 scale=128（weekly）
        req_url = mock_get.call_args[0][0]
        assert "scale=128" in req_url

    def test_fetch_raw_multiple_codes(self):
        from collectors.raw_collector import SinaKlineRawProducer
        producer = SinaKlineRawProducer()

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = '[{"day":"2025-01-01"}]'
            mock_get.return_value = mock_resp

            messages = producer.fetch_raw("raw_kline",
                                          {"codes": ["000001", "600519"]})

        assert len(messages) == 2
        assert messages[0]["key"] == "000001"
        assert messages[1]["key"] == "600519"

    def test_fetch_raw_failure(self):
        from collectors.raw_collector import SinaKlineRawProducer
        producer = SinaKlineRawProducer()

        with patch("requests.get", side_effect=ConnectionError("timeout")):
            messages = producer.fetch_raw("raw_kline", {"codes": ["000001"]})

        assert messages == []


# ============================================================
# 测试 register_producers 注册函数
# ============================================================

class TestRegisterProducers:
    """生产者注册函数测试"""

    def test_register_all_known_producers(self):
        """验证 register_producers 注册了所有启用的生产者"""
        from collectors.raw_collector import RawDataCollector, register_producers

        collector = RawDataCollector()
        with patch("config.ENABLED_SOURCES", {
            "tencent": True, "mootdx": True, "ths_hot": True,
            "ths_northbound": True, "baidu": True, "akshare_ext": True,
            "information": True, "sina_kline": True,
        }):
            register_producers(collector)

        producers = collector.list_producers()
        assert "tencent" in producers
        assert "mootdx" in producers
        assert "ths_hot" in producers
        assert "ths_northbound" in producers
        assert "baidu" in producers
        assert "akshare_ext" in producers
        assert "information" in producers
        assert "sina_kline" in producers
        assert len(producers) == 8

    def test_register_disabled_producers_skipped(self):
        """验证禁用的数据源不会被注册"""
        from collectors.raw_collector import RawDataCollector, register_producers

        collector = RawDataCollector()
        with patch("config.ENABLED_SOURCES", {
            "tencent": True, "mootdx": False,
            "ths_hot": False, "baidu": True,
            "akshare_ext": False, "information": True,
            "sina_kline": True, "ths_northbound": False,
        }):
            register_producers(collector)

        producers = collector.list_producers()
        assert "tencent" in producers
        assert "mootdx" not in producers
        assert "baidu" in producers
        assert "information" in producers
        assert "sina_kline" in producers


# ============================================================
# 测试 RawDataCollector 主调度器
# ============================================================

class TestRawDataCollector:
    """RawDataCollector 调度器单元测试"""

    def test_initial_state(self):
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        assert collector.list_producers() == []
        assert not collector.kafka_connected

    def test_register_and_list(self):
        from collectors.raw_collector import RawDataCollector, TencentRawProducer
        collector = RawDataCollector()
        collector.register(TencentRawProducer())
        assert "tencent" in collector.list_producers()
        assert len(collector.list_producers()) == 1

    def test_register_all(self):
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()

        with patch("config.ENABLED_SOURCES", {
            "tencent": True, "mootdx": True, "ths_hot": True,
            "ths_northbound": True, "baidu": True, "akshare_ext": True,
            "information": True, "sina_kline": True,
        }):
            collector.register_all()

        assert len(collector.list_producers()) == 8

    def test_get_producer_exists(self):
        from collectors.raw_collector import RawDataCollector, TencentRawProducer
        collector = RawDataCollector()
        collector.register(TencentRawProducer())
        producer = collector.get_producer("tencent")
        assert producer is not None
        assert producer.source_name() == "tencent"

    def test_get_producer_not_exists(self):
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        assert collector.get_producer("nonexistent") is None

    def test_collect_and_publish_unknown_source(self):
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        count = collector.collect_and_publish("unknown_source", "topic")
        assert count == 0

    def test_collect_and_publish_success_kafka(self):
        from collectors.raw_collector import RawDataCollector, TencentRawProducer

        collector = RawDataCollector()
        collector.register(TencentRawProducer())

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"mock_data"
            mock_urlopen.return_value = mock_resp

            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001"]):
                # 模拟 kafka 模块，避免 ImportError
                mock_kafka_mod = MagicMock()
                mock_producer = MagicMock()
                mock_kafka_mod.KafkaProducer.return_value = mock_producer
                mock_producer.send.return_value = MagicMock()

                with patch.dict("sys.modules", {"kafka": mock_kafka_mod}):
                    # 重置 Kafka 连接状态以触发重新连接
                    collector._kafka_producer = None
                    collector._kafka_enabled = False

                    count = collector.collect_and_publish("tencent", "raw_realtime")

        assert count == 1
        assert collector.kafka_connected

    def test_collect_and_publish_fallback_to_file(self):
        """Kafka 不可用时回退到本地文件"""
        from collectors.raw_collector import RawDataCollector, TencentRawProducer
        import tempfile

        collector = RawDataCollector()
        collector.register(TencentRawProducer())

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"mock_data"
            mock_urlopen.return_value = mock_resp

            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001"]):
                # 模拟 Kafka 模块，让 KafkaProducer 每次创建都抛出异常
                mock_kafka_mod = MagicMock()
                mock_kafka_mod.KafkaProducer.side_effect = Exception("connection refused")

                with patch.dict("sys.modules", {"kafka": mock_kafka_mod}):
                    with patch("config.DATA_DIR",
                               Path(tempfile.mkdtemp())):
                        collector._kafka_producer = None
                        collector._kafka_enabled = False
                        count = collector.collect_and_publish(
                            "tencent", "raw_realtime")

        assert count == 1
        assert not collector.kafka_connected

    def test_collect_and_publish_auto_topic(self):
        """topic 为空时使用默认 topic"""
        from collectors.raw_collector import RawDataCollector, TencentRawProducer

        collector = RawDataCollector()
        collector.register(TencentRawProducer())

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"mock_data"
            mock_urlopen.return_value = mock_resp

            with patch("collectors.stock_list.get_all_stock_codes",
                       return_value=["000001"]):
                mock_kafka_mod = MagicMock()
                mock_kafka_mod.KafkaProducer.side_effect = Exception("no kafka")

                with patch.dict("sys.modules", {"kafka": mock_kafka_mod}):
                    with patch("collectors.raw_collector._TOPIC_MAP",
                               {"tencent": "raw_realtime"}):
                        collector._kafka_producer = None
                        collector._kafka_enabled = False
                        count = collector.collect_and_publish("tencent")

        assert count == 1

    def test_collect_and_publish_producer_exception(self):
        """fetch_raw 抛出异常时返回 0"""
        from collectors.raw_collector import (
            RawDataCollector, RawDataProducer,
        )

        class BrokenProducer(RawDataProducer):
            def source_name(self):
                return "broken"

            def fetch_raw(self, topic, params=None):
                raise RuntimeError("broken")

        collector = RawDataCollector()
        collector.register(BrokenProducer())

        count = collector.collect_and_publish("broken", "topic")
        assert count == 0

    def test_collect_all(self):
        """collect_all 遍历所有已注册的生产者"""
        from collectors.raw_collector import RawDataCollector, TencentRawProducer

        collector = RawDataCollector()
        collector.register(TencentRawProducer())

        with patch.object(collector, "collect_and_publish",
                          return_value=1):
            results = collector.collect_all()

        assert "tencent" in results
        assert results["tencent"] == 1

    def test_collect_sources_subset(self):
        """collect_sources 只采集指定的数据源"""
        from collectors.raw_collector import RawDataCollector, TencentRawProducer

        collector = RawDataCollector()
        collector.register(TencentRawProducer())

        with patch.object(collector, "collect_and_publish",
                          return_value=1):
            results = collector.collect_sources(["tencent"])

        assert results["tencent"] == 1

    def test_health_check_all(self):
        """health_check 返回所有数据源状态"""
        from collectors.raw_collector import (
            RawDataCollector, RawDataProducer,
        )

        class GoodProducer(RawDataProducer):
            def source_name(self): return "good"
            def fetch_raw(self, topic, params=None):
                return [{"topic": topic, "key": "test", "value": "ok"}]

        class BadProducer(RawDataProducer):
            def source_name(self): return "bad"
            def fetch_raw(self, topic, params=None):
                raise RuntimeError("fail")

        collector = RawDataCollector()
        collector.register(GoodProducer())
        collector.register(BadProducer())

        status = collector.health_check()
        assert status["good"]["available"] is True
        assert status["bad"]["available"] is False

    def test_close_cleanup(self):
        """close 清理 Kafka 连接"""
        from collectors.raw_collector import RawDataCollector

        collector = RawDataCollector()
        mock_producer = MagicMock()
        collector._kafka_producer = mock_producer
        collector._kafka_enabled = True

        collector.close()

        assert collector._kafka_producer is None
        assert not collector._kafka_enabled
        mock_producer.close.assert_called_once()

    def test_close_no_kafka(self):
        """没有 Kafka 连接时 close 不报错"""
        from collectors.raw_collector import RawDataCollector
        collector = RawDataCollector()
        collector.close()  # 不应抛出异常

    def test_kafka_connection_failure(self):
        """Kafka 连接失败时 _kafka_enabled = False"""
        from collectors.raw_collector import RawDataCollector

        collector = RawDataCollector()
        mock_kafka_mod = MagicMock()
        mock_kafka_mod.KafkaProducer.side_effect = Exception("connection refused")

        with patch.dict("sys.modules", {"kafka": mock_kafka_mod}):
            collector._kafka_producer = None
            producer = collector._get_kafka_producer()

        assert producer is None
        assert not collector.kafka_connected


# ============================================================
# 测试数据流集成：RawDataCollector + DataCatalog 一致性
# ============================================================

class TestRawDataIntegration:
    """验证原始数据层与系统各层的集成一致性"""

    def test_raw_types_in_data_catalog(self):
        """验证 data_catalog 包含所有原始数据类型"""
        from pipeline.data_catalog import get_data_type_def

        raw_types = ["raw_realtime", "raw_kline", "raw_hot_reason",
                     "raw_northbound", "raw_signal", "raw_news"]
        for t in raw_types:
            type_def = get_data_type_def(t)
            assert type_def.layer == "raw"
            assert type_def.storage is not None

    def test_raw_types_in_orchestrator_groups(self):
        """验证编排器包含原始数据层的并行分组"""
        from pipeline.orchestrator import PARALLEL_GROUPS

        # 原始数据层在同一组内串行
        raw_group = None
        for group in PARALLEL_GROUPS:
            if "raw_realtime" in group:
                raw_group = group
                break

        assert raw_group is not None
        assert "raw_kline" in raw_group
        assert "raw_news" in raw_group

    def test_producer_register_to_map_consistency(self):
        """验证 _PRODUCER_REGISTRY 与 _TOPIC_MAP 的一致性

        每个注册的生产者都应该有对应的默认 topic。
        """
        from collectors.raw_collector import _PRODUCER_REGISTRY, _TOPIC_MAP
        for name in _PRODUCER_REGISTRY:
            assert name in _TOPIC_MAP, f"{name} 缺少默认 topic 映射"
