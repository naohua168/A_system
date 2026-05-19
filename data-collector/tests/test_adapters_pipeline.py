"""
适配器层 + 管道层 + 存储层 单元测试（全mock，不依赖网络/MySQL）
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


# ============================================================
# 适配器层测试
# ============================================================
class TestTencentAdapter:
    """腾讯适配器单元测试"""

    def test_supported_types(self):
        from adapters.collector_adapters import TencentAdapter
        adapter = TencentAdapter()
        types = adapter.get_supported_types()
        assert "realtime_quotes" in types
        assert "stock_basic" in types
        assert adapter.metadata.priority == 9

    def test_fetch_with_codes(self):
        from adapters.collector_adapters import TencentAdapter
        mock_result = pd.DataFrame({"code": ["000001"], "price": [12.5]})
        adapter = TencentAdapter()
        adapter._collector = MagicMock()
        adapter._collector.fetch_realtime_quotes.return_value = mock_result
        adapter._collector.fetch_all_realtime.return_value = mock_result

        from adapters.base_adapter import AdapterRequest
        req = AdapterRequest(codes=["000001"])
        df = adapter.fetch(req)
        assert not df.empty
        assert "code" in df.columns
        assert df["code"].iloc[0] == "000001"

    def test_fetch_all_realtime(self):
        from adapters.collector_adapters import TencentAdapter
        mock_result = pd.DataFrame({"code": ["000001", "600519"], "price": [12.5, 1500.0]})
        adapter = TencentAdapter()
        adapter._collector = MagicMock()
        adapter._collector.fetch_all_realtime.return_value = mock_result

        from adapters.base_adapter import AdapterRequest
        req = AdapterRequest()
        df = adapter.fetch(req)
        assert len(df) == 2


class TestMootdxAdapter:
    """Mootdx适配器单元测试"""

    def test_supported_types(self):
        from adapters.collector_adapters import MootdxAdapter
        adapter = MootdxAdapter()
        types = adapter.get_supported_types()
        assert "history_kline" in types
        assert "realtime_quotes" in types

    def test_fetch_kline(self):
        from adapters.collector_adapters import MootdxAdapter
        mock_kline = pd.DataFrame({
            "date": ["20250101", "20250102"],
            "open": [10.0, 10.1],
            "close": [10.2, 10.3],
        })
        adapter = MootdxAdapter()
        adapter._collector = MagicMock()
        adapter._collector.fetch_history_kline.return_value = mock_kline

        from adapters.base_adapter import AdapterRequest
        req = AdapterRequest(code="000001", start_date="20250101",
                              end_date="20250131", freq="daily")
        df = adapter.fetch(req)
        assert not df.empty
        assert len(df) == 2


class TestSinaKlineAdapter:
    """新浪K线适配器单元测试"""

    def test_fetch_adds_required_columns(self):
        from adapters.collector_adapters import SinaKlineAdapter
        mock_kline = pd.DataFrame({
            "date": ["20250101", "20250102"],
            "code": ["000001", "000001"],
            "open": [10.0, 10.1],
            "high": [10.5, 10.6],
            "low": [9.8, 9.9],
            "close": [10.2, 10.3],
            "volume": [1000000, 1200000],
        })
        adapter = SinaKlineAdapter()
        adapter._collector = MagicMock()
        adapter._collector.fetch_kline.return_value = mock_kline

        from adapters.base_adapter import AdapterRequest
        req = AdapterRequest(code="000001", freq="daily", days=60)
        df = adapter.fetch(req)
        assert "stock_code" in df.columns
        assert "pre_close" in df.columns
        assert "change_pct" in df.columns
        assert "amount" in df.columns
        assert "turnover_pct" in df.columns
        assert "source" in df.columns

    def test_fetch_empty_returns_empty(self):
        from adapters.collector_adapters import SinaKlineAdapter
        adapter = SinaKlineAdapter()
        adapter._collector = MagicMock()
        adapter._collector.fetch_kline.return_value = pd.DataFrame()

        from adapters.base_adapter import AdapterRequest
        req = AdapterRequest(code="000001")
        df = adapter.fetch(req)
        assert df.empty


class TestAdapterRegistry:
    """适配器注册表测试"""

    def test_register_and_get(self):
        from adapters.base_adapter import AdapterRegistry
        from adapters.collector_adapters import TencentAdapter
        AdapterRegistry.unregister_all()
        adapter = TencentAdapter()
        AdapterRegistry.register("realtime_quotes", adapter)
        adapters = AdapterRegistry.get_adapters("realtime_quotes")
        assert len(adapters) > 0
        assert adapters[0].metadata.source_name == "tencent"

    def test_get_all_types(self):
        from adapters.base_adapter import AdapterRegistry
        from adapters.collector_adapters import register_all_adapters
        AdapterRegistry.unregister_all()
        register_all_adapters()
        types = AdapterRegistry.get_all_types()
        assert "history_kline" in types
        assert "realtime_quotes" in types
        assert "hot_reason" in types


# ============================================================
# 管道层测试
# ============================================================
class TestCollectionPipeline:
    """采集管道单元测试"""

    def _setup_adapters(self):
        """重置注册表并重新注册所有适配器"""
        from adapters.base_adapter import AdapterRegistry
        from adapters.collector_adapters import register_all_adapters
        AdapterRegistry.unregister_all()
        register_all_adapters()

    def test_run_with_no_codes(self):
        self._setup_adapters()
        from pipeline.collection_pipeline import CollectionPipeline

        mock_storage = MagicMock()
        mock_storage.write.return_value = {"csv": (10, 10), "mysql": (10, 10)}

        pipeline = CollectionPipeline(storage=mock_storage)

        with patch.object(pipeline, '_collect_with_fallback',
                          return_value=(pd.DataFrame({"a": [1]}), "tencent")):
            report = pipeline.run("realtime_quotes", codes=["000001"])
            assert report is not None
            assert report.items["realtime_quotes"]["rows"] == 1

    def test_run_with_all_stocks_empty(self):
        self._setup_adapters()
        from pipeline.collection_pipeline import CollectionPipeline

        mock_storage = MagicMock()
        pipeline = CollectionPipeline(storage=mock_storage)

        with patch("collectors.stock_list.get_all_stock_codes",
                   return_value=["000001", "600519"]):
            with patch.object(pipeline, '_collect_all_stocks',
                              return_value=(pd.DataFrame(), "mootdx")):
                report = pipeline.run("history_kline")
                assert not report.items["history_kline"]["success"]

    def test_collect_with_fallback_fails(self):
        self._setup_adapters()
        from pipeline.collection_pipeline import CollectionPipeline
        from pipeline.data_catalog import get_data_type_def
        from adapters.base_adapter import AdapterRequest

        pipeline = CollectionPipeline()
        type_def = get_data_type_def("realtime_quotes")
        request = AdapterRequest()
        df, adapter = pipeline._collect_with_fallback(type_def, request)
        assert isinstance(df, pd.DataFrame)

    def test_collect_all_stocks_empty(self):
        from pipeline.collection_pipeline import CollectionPipeline
        from pipeline.data_catalog import get_data_type_def
        pipeline = CollectionPipeline()
        type_def = get_data_type_def("history_kline")
        with patch("collectors.stock_list.get_all_stock_codes",
                   return_value=[]):
            df, adapter = pipeline._collect_all_stocks(type_def)
            assert df.empty
            # 无股票时适配器名称由注册的适配器决定
            assert isinstance(adapter, str)


class TestDataCatalog:
    """数据目录测试"""

    def test_get_data_type_def_exists(self):
        from pipeline.data_catalog import get_data_type_def
        t = get_data_type_def("history_kline")
        assert t is not None
        assert t.data_type == "history_kline"
        assert t.layer == "market"

    def test_get_data_type_def_not_exists(self):
        from pipeline.data_catalog import get_data_type_def
        with pytest.raises(KeyError):
            get_data_type_def("nonexistent_type")

    def test_get_types_by_layer(self):
        from pipeline.data_catalog import get_types_by_layer
        market_types = get_types_by_layer("market")
        assert len(market_types) >= 3
        assert any(t.data_type == "history_kline" for t in market_types)

    def test_get_types_by_adapter(self):
        from pipeline.data_catalog import get_types_by_adapter
        types = get_types_by_adapter("sina_kline")
        assert len(types) >= 1
        assert types[0].data_type == "history_kline"


# ============================================================
# 存储层测试
# ============================================================
class TestCsvStorage:
    """CSV存储后端测试"""

    def test_write_empty(self):
        from storage.storage_manager import CsvStorage
        storage = CsvStorage()
        written, total = storage.write("test_table", pd.DataFrame())
        assert written == 0
        assert total == 0

    def test_write_and_read(self, tmp_path):
        from storage.storage_manager import CsvStorage
        storage = CsvStorage(base_dir=tmp_path)
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        written, total = storage.write("test_table", df)
        assert written == 3

        read_df = storage.read("test_table", limit=5)
        assert not read_df.empty
        assert len(read_df) == 3

    def test_read_empty(self, tmp_path):
        from storage.storage_manager import CsvStorage
        storage = CsvStorage(base_dir=tmp_path)
        df = storage.read("nonexistent")
        assert df.empty

    def test_get_latest(self, tmp_path):
        from storage.storage_manager import CsvStorage
        storage = CsvStorage(base_dir=tmp_path)
        df = storage.get_latest("nonexistent", "code", "000001")
        assert df.empty


class TestMysqlStorage:
    """MySQL存储后端测试（mock模式，不依赖真实MySQL）"""

    def test_write_empty(self):
        from storage.storage_manager import MysqlStorage
        storage = MysqlStorage()
        written, total = storage.write("stock", pd.DataFrame())
        assert written == 0
        assert total == 0

    def test_column_mapping_exists(self):
        from storage.storage_manager import MysqlStorage
        mapping = MysqlStorage.COLUMN_MAP
        assert "stock" in mapping
        assert "stock_daily" in mapping
        assert "code" in mapping["stock"]
        assert mapping["stock"]["code"] == "stock_code"

    def test_validation_rules(self):
        from storage.storage_manager import MysqlStorage
        rules = MysqlStorage.VALIDATION_RULES
        assert "stock" in rules
        assert "stock_daily" in rules
        assert "require_non_null" in rules["stock_daily"]


# ============================================================
# 配置层测试
# ============================================================
class TestConfig:
    """配置层测试"""

    def test_enabled_sources(self):
        from config import ENABLED_SOURCES
        assert "mootdx" in ENABLED_SOURCES
        assert "tencent" in ENABLED_SOURCES
        assert "sina_kline" in ENABLED_SOURCES

    def test_mysql_config_exists(self):
        from config import MYSQL_CONFIG
        assert "host" in MYSQL_CONFIG
        assert "port" in MYSQL_CONFIG
        assert "user" in MYSQL_CONFIG
        assert "password" in MYSQL_CONFIG

    def test_kafka_config_exists(self):
        from config import KAFKA_CONFIG
        assert "bootstrap_servers" in KAFKA_CONFIG
        assert "topics" in KAFKA_CONFIG
        assert "realtime" in KAFKA_CONFIG["topics"]

    def test_kline_config(self):
        from config import KLINE_COLLECT_INTERVAL, KLINE_RECONNECT_MAX_RETRIES
        assert KLINE_COLLECT_INTERVAL > 0
        assert KLINE_RECONNECT_MAX_RETRIES > 0
