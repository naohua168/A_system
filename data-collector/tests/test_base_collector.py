"""
数据采集基类单元测试
"""

import pytest
import pandas as pd


class TestBaseCollector:
    """测试数据采集器公共接口行为"""

    def test_imports(self):
        """验证模块可正确导入"""
        from collectors.base_collector import BaseCollector
        assert BaseCollector is not None

    def test_collector_has_required_methods(self):
        """验证采集器接口定义了必要方法"""
        from collectors.base_collector import BaseCollector
        methods = ["health_check", "fetch_history_kline", "fetch_realtime_quotes"]
        for m in methods:
            assert hasattr(BaseCollector, m), f"缺少方法: {m}"


class TestDataSourceFactory:
    """测试数据源工厂"""

    def test_import_and_create(self):
        from collectors.data_source_factory import DataSourceFactory
        factory = DataSourceFactory()
        assert factory is not None

    def test_list_supported_sources(self):
        from collectors.data_source_factory import DataSourceFactory
        factory = DataSourceFactory()
        sources = factory.list_supported_sources()
        assert isinstance(sources, list)
        assert len(sources) > 0
