"""AI Agent单元测试"""
import os
import pytest
from app.agents.base_agent import BaseAgent
from app.models.simulation import SimulationEngine

# 条件跳过：无 API Key 时跳过需要调用 LLM 的测试
has_api_key = bool(os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))
skip_no_api = pytest.mark.skipif(not has_api_key, reason="需要配置 API Key")


class TestBaseAgent:
    def test_base_agent_is_abstract(self):
        with pytest.raises(TypeError):
            BaseAgent("test", "测试")  # 抽象类无法实例化

    def test_base_agent_init(self, fundamentals_analyst):
        assert fundamentals_analyst.name == "fundamentals_analyst"
        assert fundamentals_analyst.role == "基本面分析师"
        assert fundamentals_analyst.system_prompt != ""

    def test_agent_has_analyze_method(self, fundamentals_analyst):
        assert hasattr(fundamentals_analyst, "analyze")
        assert callable(fundamentals_analyst.analyze)

    def test_agent_has_chat_method(self, fundamentals_analyst):
        assert hasattr(fundamentals_analyst, "chat")
        assert callable(fundamentals_analyst.chat)


class TestFundamentalsAnalyst:
    def test_name(self, fundamentals_analyst):
        assert fundamentals_analyst.name == "fundamentals_analyst"

    def test_role(self, fundamentals_analyst):
        assert "基本面" in fundamentals_analyst.role

    @skip_no_api
    def test_analyze_returns_dict(self, fundamentals_analyst, mock_context):
        import asyncio
        result = asyncio.run(fundamentals_analyst.analyze(mock_context))
        assert isinstance(result, dict)


class TestTechnicalAnalyst:
    def test_name(self, technical_analyst):
        assert technical_analyst.name == "technical_analyst"

    def test_role_contains_technical(self, technical_analyst):
        assert "技术" in technical_analyst.role


class TestTraderAgent:
    def test_name(self, trader_agent):
        assert trader_agent.name == "trader_agent"

    def test_decide_direction(self, trader_agent, mock_context):
        reports = mock_context["agent_reports"]
        direction = trader_agent._decide_direction(reports)
        assert direction in ["买入", "卖出", "持有"]


class TestRiskManager:
    def test_name(self, risk_manager):
        assert risk_manager.name == "risk_manager"

    def test_assess_risk(self, risk_manager):
        # risk_score = volatility*0.6 + (1-confidence/10)*0.4
        # confidence=8, vol=0.15 → risk_score=0.15*0.6+0.2*0.4=0.17 → "较低"
        # confidence=6, vol=0.25 → risk_score=0.25*0.6+0.4*0.4=0.31 → "中"
        # confidence=4, vol=0.35 → risk_score=0.35*0.6+0.6*0.4=0.45 → "较高"
        assert risk_manager._assess_risk("买入", 8, 0.15) == "较低"
        assert risk_manager._assess_risk("买入", 6, 0.25) == "中"
        assert risk_manager._assess_risk("买入", 4, 0.35) == "较高"


class TestSimulationEngine:
    def test_get_simulation_returns_string(self):
        result = SimulationEngine.get_simulation("fundamentals_analyst", {"stock_code": "000001"})
        assert isinstance(result, str)
        assert len(result) > 10

    def test_get_simulation_contains_stock_code(self):
        result = SimulationEngine.get_simulation("trader_agent", {"stock_code": "600519", "direction": "买入"})
        assert "600519" in result or "买入" in result

    def test_analyze_with_simulation_returns_dict(self):
        result = SimulationEngine.analyze_with_simulation("technical_analyst", "300750")
        assert isinstance(result, dict)
        assert result["agent"] == "technical_analyst"
        assert result["stock_code"] == "300750"
        assert result["mode"] == "simulation"

    def test_unknown_role_returns_fallback(self):
        result = SimulationEngine.get_simulation("unknown_role", {})
        assert isinstance(result, str)


class TestMemoryService:
    def test_init_creates_dir(self, memory_service):
        assert memory_service.MEMORY_DIR.exists()

    def test_load_history_empty(self, memory_service):
        import asyncio
        history = asyncio.run(memory_service.load_history("NONEXIST"))
        assert history == []

    def test_save_and_load_decision(self, memory_service):
        import asyncio
        # 清理之前测试运行留下的历史记录
        test_file = memory_service.MEMORY_DIR / "TEST001.json"
        if test_file.exists():
            test_file.unlink()
        decision = {"direction": "买入", "position": "30%"}
        asyncio.run(memory_service.save_decision("TEST001", decision))
        history = asyncio.run(memory_service.load_history("TEST001"))
        assert len(history) == 1
        assert history[0]["decision"]["direction"] == "买入"

    def test_auto_reflect_with_single_record(self, memory_service):
        import asyncio
        result = asyncio.run(memory_service.auto_reflect("NONEXIST"))
        assert "message" in result
