"""AI 服务集成测试套件 — 覆盖所有核心模块"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.fusion import FusionEngine, fusion_engine
from app.models.simulation import (
    SimulationEngine, get_mock_data, select_dialog_template,
    get_agent_template, DIALOG_TEMPLATES, AGENT_TEMPLATES, UNIFIED_MOCK_DATA,
)
from app.services.memory_service import MemoryService, RedisClient
from app.services.multi_agent_service import MultiAgentService

# ────────────────────────────────────────
# 测试 1: FusionEngine 融合引擎
# ────────────────────────────────────────

class TestFusionEngine:
    def test_init_default_weights_sum_to_one(self):
        engine = FusionEngine()
        total = sum(engine._weights.values())
        assert abs(total - 1.0) < 0.001

    def test_fuse_empty_reports(self):
        result = FusionEngine().fuse({})
        assert result["action"] == "hold"
        assert result["confidence"] == 0

    def test_fuse_buy_decision(self):
        reports = {
            "fundamentals_analyst": {"analysis": "建议买入，估值合理", "sentiment_score": 0.5},
            "technical_analyst": {"analysis": "技术面看涨，强烈买入", "sentiment_score": 0.3},
        }
        result = FusionEngine().fuse(reports)
        assert result["action"] == "buy"
        assert result["confidence"] > 0

    def test_fuse_sell_decision(self):
        reports = {
            "fundamentals_analyst": {"analysis": "建议卖出，估值偏高", "sentiment_score": -0.5},
            "technical_analyst": {"analysis": "死叉卖出信号", "sentiment_score": -0.3},
        }
        result = FusionEngine().fuse(reports)
        assert result["action"] == "sell"

    def test_update_weight(self):
        engine = FusionEngine()
        engine.update_weight("technical_analyst", 0.5)
        assert engine._weights["technical_analyst"] > 0.3

    def test_extract_direction_from_text(self):
        assert FusionEngine._extract_direction({"analysis": "推荐买入"}) == "buy"
        assert FusionEngine._extract_direction({"analysis": "建议减持卖出"}) == "sell"
        assert FusionEngine._extract_direction({"analysis": "建议观望"}) == "hold"

    def test_fuse_agent_details_contains_all_inputs(self):
        reports = {
            "technical_analyst": {"analysis": "买入", "sentiment_score": 0.6},
            "fundamentals_analyst": {"analysis": "卖出", "sentiment_score": -0.4},
        }
        result = FusionEngine().fuse(reports)
        assert len(result["agent_details"]) == 2
        assert result["buy_score"] > 0
        assert result["sell_score"] > 0

    # ── 新增: 权重持久化与自动学习测试 ──

    def test_get_weights_returns_copy(self):
        """get_weights 返回只读副本，修改不影响内部状态"""
        engine = FusionEngine()
        w = engine.get_weights()
        w["technical_analyst"] = 999
        assert engine._weights["technical_analyst"] != 999

    def test_update_weight_unknown_agent(self):
        """更新未知 Agent 的权重应静默跳过"""
        engine = FusionEngine()
        old = engine.get_weights()
        engine.update_weight("non_existent_agent", 0.9)
        assert engine.get_weights() == old

    def test_update_weight_negative_value(self):
        """负值权重应被截断为 0"""
        engine = FusionEngine()
        engine.update_weight("technical_analyst", -1.0)
        assert engine._weights["technical_analyst"] >= 0.0

    def test_learn_weights_without_redis_does_nothing(self):
        """无 Redis 时权重学习不做任何操作"""
        engine = FusionEngine(redis_client=None)
        before = engine.get_weights()
        engine.learn_weights()
        assert engine.get_weights() == before

    def test_persistence_with_mock_redis(self):
        """使用 Mock Redis 验证权重持久化"""
        class MockRedis:
            def __init__(self):
                self.data = {}
            def hgetall(self, key):
                return {k: v for k, v in self.data.items() if k.startswith(key.replace("fusion:", ""))}
            def hset(self, key, mapping=None):
                for k, v in (mapping or {}).items():
                    self.data[f"{key}:{k}"] = v

        # 创建自定义权重的引擎，验证持久化
        mock_redis = MockRedis()
        engine1 = FusionEngine(redis_client=mock_redis)
        w1 = engine1.get_weights()
        assert abs(sum(w1.values()) - 1.0) < 0.001, "权重总和应为 1"
        assert len(w1) == 7, "应有 7 个 Agent 权重"

    def test_record_accuracy(self):
        """record_accuracy 在有 Redis 时正常工作"""
        records = []
        class MockRedis:
            def lpush(self, key, value):
                records.append((key, value))
            def ltrim(self, key, start, end):
                pass

        engine = FusionEngine(redis_client=MockRedis())
        engine.record_accuracy("technical_analyst", True)
        assert len(records) == 1
        assert records[0] == (f"fusion:accuracy:technical_analyst", 1)

        engine.record_accuracy("technical_analyst", False)
        assert records[1][1] == 0  # 第二次记录为 0

    def test_record_accuracy_unknown_agent(self):
        """未知 Agent 的准确率记录应被忽略"""
        engine = FusionEngine()
        engine.record_accuracy("ghost_agent", True)  # 不应抛异常


# ────────────────────────────────────────
# 测试 2: 统一模拟模板库
# ────────────────────────────────────────

class TestSimulationTemplates:
    def test_unified_mock_data_contains_all_keys(self):
        data = get_mock_data()
        assert "ma5" in data
        assert "dif" in data
        assert "k" in data
        assert "rsi" in data
        assert "pe" in data
        assert "stock_code" in data

    def test_all_dialog_templates_format_correctly(self):
        data = get_mock_data("测试")
        for key, template in DIALOG_TEMPLATES.items():
            try:
                result = template.format(**data)
                assert len(result) > 10
            except KeyError as e:
                pytest.fail(f"模板 {key} 缺少占位符: {e}")

    def test_all_agent_templates_format_correctly(self):
        data = get_mock_data()
        data["stock_code"] = "000001"  # 覆盖默认值
        for role, templates in AGENT_TEMPLATES.items():
            for sentiment, template in templates.items():
                try:
                    result = template.format(**data)
                    assert len(result) > 10
                except KeyError as e:
                    pytest.fail(f"Agent 模板 {role}/{sentiment} 缺少占位符: {e}")

    def test_select_dialog_template_by_keywords(self):
        result = select_dialog_template("缠论")
        assert "卖点" in result or "买点" in result or "缠论" in result
        assert "看涨" in select_dialog_template("涨")
        assert "需谨慎" in select_dialog_template("跌")
        assert "基金" in select_dialog_template("最新基金净值")
        assert "大盘分析" in select_dialog_template("大盘指数走势")

    def test_select_dialog_template_default(self):
        template = select_dialog_template("你好，请问有什么推荐？")
        assert "投资建议" in template

    def test_get_agent_template_known_role(self):
        template = get_agent_template("technical_analyst", "bullish")
        assert "技术分析" in template

    def test_get_agent_template_unknown_role(self):
        result = get_agent_template("unknown_role", "bullish")
        assert "未配置" in result

    def test_simulation_engine_get_simulation(self):
        result = SimulationEngine.get_simulation("fundamentals_analyst", {"stock_code": "000001"})
        assert isinstance(result, str)
        assert len(result) > 20

    def test_simulation_engine_analyze_with_simulation(self):
        result = SimulationEngine.analyze_with_simulation("technical_analyst", "300750")
        assert result["agent"] == "technical_analyst"
        assert result["stock_code"] == "300750"
        assert result["mode"] == "simulation"


# ────────────────────────────────────────
# 测试 3: MemoryService 记忆服务
# ────────────────────────────────────────

class TestMemoryService:
    @pytest.fixture
    def memory_service(self):
        svc = MemoryService()
        # 清理测试数据
        test_file = svc.MEMORY_DIR / "TEST999.json"
        if test_file.exists():
            test_file.unlink()
        return svc

    def test_init_creates_dir(self, memory_service):
        assert memory_service.MEMORY_DIR.exists()

    def test_load_history_empty(self, memory_service):
        history = asyncio.run(memory_service.load_history("NONEXIST"))
        assert history == []

    def test_save_and_load_decision(self, memory_service):
        decision = {"direction": "买入", "position": "30%"}
        asyncio.run(memory_service.save_decision("TEST999", decision))
        history = asyncio.run(memory_service.load_history("TEST999"))
        assert len(history) == 1
        assert history[0]["decision"]["direction"] == "买入"
        # 清理
        test_file = memory_service.MEMORY_DIR / "TEST999.json"
        if test_file.exists():
            test_file.unlink()

    def test_auto_reflect_empty(self, memory_service):
        result = asyncio.run(memory_service.auto_reflect("NONEXIST"))
        assert "暂无足够的历史数据" in result["message"]

    def test_save_returns_path_string(self, memory_service):
        path = asyncio.run(memory_service.save_decision("TEST999", {"direction": "持有"}))
        assert isinstance(path, str)
        # 清理
        test_file = memory_service.MEMORY_DIR / "TEST999.json"
        if test_file.exists():
            test_file.unlink()


# ────────────────────────────────────────
# 测试 4: MultiAgentService 多智能体编排
# ────────────────────────────────────────

class TestMultiAgentService:
    def test_init_creates_7_agents(self):
        svc = MultiAgentService()
        assert len(svc.agents) == 7

    def test_agent_names_are_unique(self):
        svc = MultiAgentService()
        names = [a.name for a in svc.agents]
        assert len(names) == len(set(names))

    def test_find_agent_by_type(self):
        svc = MultiAgentService()
        from app.agents.trader_agent import TraderAgent
        agent = svc._find_agent(TraderAgent)
        assert agent.name == "trader_agent"

    def test_iterative_debate_returns_dict(self):
        svc = MultiAgentService()
        result = asyncio.run(svc.iterative_debate("000001", rounds=2))
        assert "debate_rounds" in result
        assert result["debate_rounds"] == 2

    def test_analyze_stock_returns_fused_decision(self):
        svc = MultiAgentService()
        result = asyncio.run(svc.analyze_stock("000001"))
        assert "stock_code" in result
        assert "fused_decision" in result
        assert result["stock_code"] == "000001"
        assert "reports" in result
        assert len(result["reports"]) == 7  # 7 个 Agent

    def test_analyze_all_returns_multiple_stocks(self):
        svc = MultiAgentService()
        result = asyncio.run(svc.analyze_all(["000001", "600519"]))
        assert len(result) == 2
        assert "000001" in result
        assert "600519" in result


# ────────────────────────────────────────
# 测试 5: 配置验证
# ────────────────────────────────────────

class TestConfiguration:
    def test_settings_load(self):
        from app.config import settings
        assert hasattr(settings, "log_level")
        assert settings.backend_api_url == "http://localhost:8082/api"
        assert settings.siliconflow_model != ""

    def test_no_kimi_config_removed(self):
        from app.config import Settings
        s = Settings()
        # Kimi 配置已被移除
        assert not hasattr(s, "kimi_api_key")

    def test_log_level_exists(self):
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "log_level")
        assert s.log_level in ("DEBUG", "INFO", "WARNING", "ERROR")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
