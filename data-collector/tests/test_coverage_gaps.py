"""
数据采集层补充单元测试
覆盖现有测试空白：CircuitBreaker、数据校验、适配器注册表、数据目录
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pytest
import pandas as pd
from unittest.mock import MagicMock, PropertyMock
from collectors.base_collector import CircuitBreaker
from collectors.data_source_factory import DataSourceFactory
from adapters.base_adapter import (
    AdapterRequest, AdapterMetadata, AdapterRegistry
)
from pipeline.data_catalog import (
    DATA_CATALOG, DataTypeDef, StorageTarget
)


# ============================================================
# CircuitBreaker 状态机测试
# ============================================================

class TestCircuitBreaker:
    """熔断器三态状态机测试"""

    def setup_method(self):
        CircuitBreaker._state.clear()

    def test_initial_state_closed(self):
        cb = CircuitBreaker("test_source")
        assert cb._s["state"] == "closed"
        assert cb._s["failure_count"] == 0

    def test_allow_request_when_closed(self):
        cb = CircuitBreaker("test_source")
        assert cb.allow_request() is True

    def test_transition_to_open_after_threshold(self):
        cb = CircuitBreaker("test_source", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb._s["state"] == "closed"
        cb.record_failure()
        assert cb._s["state"] == "open"

    def test_deny_request_when_open(self):
        cb = CircuitBreaker("test_source", failure_threshold=1)
        cb.record_failure()
        assert cb.allow_request() is False

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker("test_source", failure_threshold=1, recovery_timeout=-1)
        cb.record_failure()
        cb.allow_request()
        assert cb._s["state"] == "half_open"

    def test_half_open_limited_attempts(self):
        cb = CircuitBreaker("test_source", failure_threshold=1, recovery_timeout=-1)
        cb.record_failure()
        # Call 1: open→half_open (attempts=0)
        assert cb.allow_request() is True
        # Call 2-4: half_open, attempts 0→1, 1→2, 2→3
        assert cb.allow_request() is True
        assert cb.allow_request() is True
        assert cb.allow_request() is True
        # Call 5: half_open, attempts=3 NOT < 3 → denied
        assert cb.allow_request() is False

    def test_record_success_closes_circuit(self):
        cb = CircuitBreaker("test_source", failure_threshold=1)
        cb.record_failure()
        cb._s["state"] = "half_open"
        cb.record_success()
        assert cb._s["state"] == "closed"
        assert cb._s["failure_count"] == 0

    def test_multiple_sources_isolated(self):
        cb1 = CircuitBreaker("source_a", failure_threshold=1)
        cb2 = CircuitBreaker("source_b", failure_threshold=1)
        cb1.record_failure()
        assert cb1._s["state"] == "open"
        assert cb2._s["state"] == "closed"


# ============================================================
# AdapterRequest 数据类测试
# ============================================================

class TestAdapterRequest:
    def test_default_fields(self):
        req = AdapterRequest(codes=["000001"])
        assert req.codes == ["000001"]
        assert req.freq == "daily"
        assert req.days == 30

    def test_custom_fields(self):
        req = AdapterRequest(
            codes=["000001", "600519"],
            start_date="20250101",
            end_date="20250131",
            freq="weekly",
            days=120,
            top_n=50,
        )
        assert len(req.codes) == 2
        assert req.freq == "weekly"
        assert req.days == 120

    def test_fetch_id_is_generated(self):
        req = AdapterRequest(code="000001")
        assert len(req.fetch_id) == 15

    def test_extra_defaults(self):
        req = AdapterRequest()
        assert req.extra == {}
        assert req.top_n == 20


# ============================================================
# AdapterMetadata 数据类测试
# ============================================================

class TestAdapterMetadata:
    def test_default_fields(self):
        meta = AdapterMetadata(source_name="tencent", priority=100)
        assert meta.source_name == "tencent"
        assert meta.priority == 100
        assert meta.supported_data_types == []
        assert meta.failure_count == 0

    def test_with_data_types(self):
        meta = AdapterMetadata(
            source_name="test_source",
            priority=50,
            supported_data_types=["realtime_quotes", "stock_basic"],
            description="测试适配器",
        )
        assert "realtime_quotes" in meta.supported_data_types
        assert meta.description == "测试适配器"


# ============================================================
# AdapterRegistry 注册表测试
# ============================================================

class TestAdapterRegistry:
    def setup_method(self):
        AdapterRegistry.unregister_all()

    def test_register_and_retrieve(self):
        adapter = MagicMock()
        type(adapter).metadata = PropertyMock(
            return_value=AdapterMetadata(source_name="mock", priority=50)
        )
        AdapterRegistry.register("realtime_quotes", adapter)
        adapters = AdapterRegistry.get_adapters("realtime_quotes")
        assert len(adapters) == 1
        assert adapters[0] == adapter

    def test_get_adapters_returns_empty_for_unknown_type(self):
        assert AdapterRegistry.get_adapters("nonexistent") == []

    def test_multiple_adapters_sorted_by_priority(self):
        low = MagicMock()
        type(low).metadata = PropertyMock(
            return_value=AdapterMetadata(source_name="low", priority=10)
        )
        high = MagicMock()
        type(high).metadata = PropertyMock(
            return_value=AdapterMetadata(source_name="high", priority=100)
        )
        AdapterRegistry.register("realtime", low)
        AdapterRegistry.register("realtime", high)
        adapters = AdapterRegistry.get_adapters("realtime")
        assert adapters[0].metadata.source_name == "high"

    def test_get_all_types_returns_registered_types(self):
        a1 = MagicMock()
        type(a1).metadata = PropertyMock(return_value=AdapterMetadata(source_name="a1", priority=0))
        AdapterRegistry.register("type_a", a1)
        AdapterRegistry.register("type_b", a1)
        types = AdapterRegistry.get_all_types()
        assert "type_a" in types
        assert "type_b" in types

    def test_unregister_all_clears(self):
        a1 = MagicMock()
        type(a1).metadata = PropertyMock(return_value=AdapterMetadata(source_name="a1", priority=0))
        AdapterRegistry.register("test_type", a1)
        assert len(AdapterRegistry.get_all_types()) > 0
        AdapterRegistry.unregister_all()
        assert AdapterRegistry.get_all_types() == []


# ============================================================
# DataSourceFactory 测试
# ============================================================

class TestDataSourceFactory:
    def test_list_supported_sources(self):
        sources = DataSourceFactory.list_supported_sources()
        assert isinstance(sources, list)
        assert len(sources) > 0
        assert "tencent" in sources

    def test_check_data_quality_valid(self):
        df = pd.DataFrame({
            "code": ["000001", "600519"],
            "price": [10.5, 1500.0],
            "volume": [100, 200],
        })
        result = DataSourceFactory._check_data_quality(df, "realtime")
        # 返回清洗后的 DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_check_data_quality_empty(self):
        df = pd.DataFrame()
        result = DataSourceFactory._check_data_quality(df, "realtime")
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ============================================================
# DataCatalog 测试
# ============================================================

class TestDataCatalog:
    def test_catalog_is_non_empty(self):
        assert len(DATA_CATALOG) > 0

    def test_each_entry_has_required_fields(self):
        for entry in DATA_CATALOG:
            assert entry.data_type
            assert entry.display_name
            assert entry.layer

    def test_realtime_quotes_exists(self):
        matches = [d for d in DATA_CATALOG if d.data_type == "realtime_quotes"]
        assert len(matches) == 1
        assert "tencent" in matches[0].source_order

    def test_storage_target_defaults(self):
        target = StorageTarget()
        assert target.mysql_table is None
        assert target.csv_prefix is None
        assert target.retention_days == 30

    def test_storage_target_custom(self):
        target = StorageTarget(mysql_table="stock_daily", retention_days=90)
        assert target.mysql_table == "stock_daily"
        assert target.retention_days == 90
