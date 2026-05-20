"""
AI 服务核心模块全面单元测试 — 60+ 测试用例覆盖所有模块
运行方式: python -m pytest tests/test_core_comprehensive.py -v
"""

import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.models.deepseek_client import AIClient, client as deepseek_client
from app.models.simulation import (
    SimulationEngine, get_mock_data, select_dialog_template,
    get_agent_template, DIALOG_TEMPLATES, AGENT_TEMPLATES, UNIFIED_MOCK_DATA,
)
from app.models.model_registry import ModelRegistry
from app.services.memory_service import MemoryService
from app.services.multi_agent_service import MultiAgentService
from app.services.dialogue_service import DialogueService


# ============================================================
# 1. AIClient 模拟模式测试
# ============================================================

class TestAIClientMockMode:
    """测试 AIClient 在无 API Key 时的模拟模式"""

    def test_auto_mock_mode_when_no_api_key(self):
        """验证无 API Key 时自动启用模拟模式"""
        with patch.object(settings, "siliconflow_api_key", ""):
            with patch.object(settings, "deepseek_api_key", ""):
                client = AIClient()
                assert client.mock_mode is True
                assert client.status["mode"] == "mock"
                assert "API Key" in client.status["hint"] or "环境变量" in client.status["hint"]

    def test_real_mode_when_deepseek_key_configured(self):
        """验证仅配 DeepSeek Key 时使用 DeepSeek 后端"""
        with patch.object(settings, "siliconflow_api_key", ""):
            with patch.object(settings, "deepseek_api_key", "sk-test-key"):
                client = AIClient()
                assert client.mock_mode is False
                assert client.backend == "deepseek"
                assert client.status["mode"] == "real"
                assert "deepseek" in client.status["hint"]

    def test_real_mode_when_siliconflow_key_configured(self):
        """验证配了 SiliconFlow Key 时优先使用该后端（当前实际配置）"""
        client = AIClient()
        assert client.mock_mode is False
        assert client.backend == "siliconflow"
        assert client.status["mode"] == "real"
        assert "siliconflow" in client.status["hint"]

    def test_siliconflow_fallsback_to_deepseek(self):
        """验证 SiliconFlow 和 DeepSeek 全配时优先使用 SiliconFlow"""
        with patch.object(settings, "siliconflow_api_key", "sf-key-123"):
            with patch.object(settings, "deepseek_api_key", "ds-key-456"):
                client = AIClient()
                assert client.mock_mode is False
                assert client.backend == "siliconflow"

    @pytest.mark.asyncio
    async def test_mock_chat_returns_rich_reply(self):
        """验证模拟模式下 chat 返回有意义的回复"""
        with patch.object(settings, "siliconflow_api_key", ""):
            with patch.object(settings, "deepseek_api_key", ""):
                client = AIClient()
                reply = await client.chat([{"role": "user", "content": "请分析000001"}])
                assert isinstance(reply, str)
                assert len(reply) > 20
                assert "风险" in reply or "建议" in reply or "分析" in reply

    @pytest.mark.asyncio
    async def test_mock_chat_with_chanlun_query(self):
        """验证缠论查询触发对应模板"""
        with patch.object(settings, "siliconflow_api_key", ""):
            with patch.object(settings, "deepseek_api_key", ""):
                client = AIClient()
                reply = await client.chat([{"role": "user", "content": "缠论买点分析"}])
                assert "买点" in reply or "中枢" in reply

    @pytest.mark.asyncio
    async def test_mock_chat_with_fund_query(self):
        """验证基金查询触发对应模板"""
        with patch.object(settings, "siliconflow_api_key", ""):
            with patch.object(settings, "deepseek_api_key", ""):
                client = AIClient()
                reply = await client.chat([{"role": "user", "content": "基金净值查询"}])
                assert "基金" in reply or "净值" in reply

    def test_status_property(self):
        """验证 status 属性字段完整性"""
        with patch.object(settings, "siliconflow_api_key", ""):
            with patch.object(settings, "deepseek_api_key", ""):
                client = AIClient()
                s = client.status
                assert "mode" in s
                assert "model" in s
                assert "api_configured" in s
                assert s["api_configured"] is False

    def test_siliconflow_status_fields(self):
        """验证 SiliconFlow 模式 status 字段完整"""
        client = AIClient()
        s = client.status
        assert all(k in s for k in ("mode", "model", "backend", "api_configured", "hint"))
        assert s["mode"] == "real"
        assert s["api_configured"] is True
        assert s["backend"] == "siliconflow"


# ============================================================
# 2. TechnicalAnalyst 信号决策逻辑测试
# ============================================================

class TestTechnicalAnalystSignal:
    """技术分析师信号判断算法测试"""

    @pytest.fixture
    def analyst(self):
        from app.agents.technical_analyst import TechnicalAnalyst
        return TechnicalAnalyst()

    def test_strong_buy_signal(self, analyst):
        """MA5>MA10>MA20 + MACD金叉 + RSI偏强 → strong_buy"""
        data = {
            "ma5": 16, "ma10": 15.5, "ma20": 15, "ma60": 14,
            "dif": 0.5, "dea": 0.3, "macd": 0.2,
            "k": 70, "d": 65, "j": 80,
            "rsi": 65, "close": 16.2,
            "boll_up": 17, "boll_mid": 15, "boll_low": 13,
            "cci": 150, "wr": -15,
        }
        assert analyst._determine_signal(data) == "strong_buy"

    def test_strong_sell_signal(self, analyst):
        """MA5<MA10<MA20 + MACD死叉 + RSI偏弱 → strong_sell"""
        data = {
            "ma5": 14, "ma10": 14.5, "ma20": 15, "ma60": 15.5,
            "dif": -0.3, "dea": -0.1, "macd": -0.2,
            "k": 35, "d": 40, "j": 25,
            "rsi": 35, "close": 13.8,
            "boll_up": 16, "boll_mid": 15, "boll_low": 14,
            "cci": -120, "wr": -85,
        }
        assert analyst._determine_signal(data) == "strong_sell"

    def test_neutral_signal_mixed(self, analyst):
        """混合信号应返回合理结果（非空字符串）"""
        data = {
            "ma5": 15.1, "ma10": 15.2, "ma20": 15.0, "ma60": 15.5,
            "dif": 0.05, "dea": 0.06, "macd": -0.01,
            "k": 50, "d": 51, "j": 48,
            "rsi": 50, "close": 15.1,
            "boll_up": 16, "boll_mid": 15.0, "boll_low": 14,
            "cci": 0, "wr": -50,
        }
        signal = analyst._determine_signal(data)
        assert isinstance(signal, str) and signal != ""

    def test_buy_signal_moderate(self, analyst):
        """温和看多 → 返回有效信号字符串"""
        data = {
            "ma5": 15.3, "ma10": 15.2, "ma20": 15.1, "ma60": 15.0,
            "dif": 0.1, "dea": 0.05, "macd": 0.05,
            "k": 55, "d": 52, "j": 61,
            "rsi": 55, "close": 15.2,
            "boll_up": 16, "boll_mid": 15.1, "boll_low": 14,
            "cci": 60, "wr": -50,
        }
        signal = analyst._determine_signal(data)
        assert signal in ("strong_buy", "buy", "neutral", "sell", "strong_sell")

    def test_signal_with_missing_data(self, analyst):
        """数据缺失时返回 neutral"""
        assert analyst._determine_signal({}) == "neutral"

    def test_signal_with_invalid_data(self, analyst):
        """无效数据类型时返回 neutral"""
        data = {"ma5": "bad", "ma10": None}
        assert analyst._determine_signal(data) == "neutral"

    def test_mock_analysis_bullish(self, analyst):
        """bullish 信号下的模拟分析包含看涨关键词"""
        data = {
            "ma5": 16, "ma10": 15.5, "ma20": 15, "ma60": 14,
            "dif": 0.5, "dea": 0.3, "macd": 0.2,
            "k": 70, "d": 65, "j": 80,
            "rsi": 65, "close": 16.2,
            "boll_up": 17, "boll_mid": 15, "boll_low": 13,
            "cci": 150, "wr": -15,
        }
        result = analyst._mock_analysis(data)
        assert "看涨" in result or "多头" in result

    def test_mock_analysis_bearish(self, analyst):
        """bearish 信号下的模拟分析包含看跌关键词"""
        data = {
            "ma5": 14, "ma10": 14.5, "ma20": 15, "ma60": 15.5,
            "dif": -0.3, "dea": -0.1, "macd": -0.2,
            "k": 35, "d": 40, "j": 25, "rsi": 35,
            "close": 13.8, "boll_up": 16, "boll_mid": 15, "boll_low": 14,
        }
        result = analyst._mock_analysis(data)
        assert "需谨慎" in result or "减仓" in result


# ============================================================
# 3. Agent 各角色模拟分析测试
# ============================================================

class TestFundamentalsAnalystMock:
    """基本面分析师模拟分析测试"""

    @pytest.mark.asyncio
    async def test_mock_analysis_low_pe(self):
        from app.agents.fundamentals_analyst import FundamentalsAnalyst
        agent = FundamentalsAnalyst()
        text = agent._mock_analysis({"pe": 10, "pb": 1.2, "stockName": "测试银行", "industry": "银行"})
        assert "低估" in text
        assert "分批建仓" in text

    @pytest.mark.asyncio
    async def test_mock_analysis_high_pe(self):
        from app.agents.fundamentals_analyst import FundamentalsAnalyst
        agent = FundamentalsAnalyst()
        text = agent._mock_analysis({"pe": 60, "pb": 8, "stockName": "测试科技", "industry": "科技"})
        assert "高估" in text
        assert "谨慎" in text

    def test_mock_stock_data(self):
        from app.agents.fundamentals_analyst import FundamentalsAnalyst
        agent = FundamentalsAnalyst()
        data = agent._mock_stock_data("000001")
        assert data["stockCode"] == "000001"
        assert data["pe"] == 25.6


class TestSentimentAnalystMock:
    """情绪分析师模拟分析测试"""

    @pytest.fixture
    def analyst(self):
        from app.agents.sentiment_analyst import SentimentAnalyst
        return SentimentAnalyst()

    def test_determine_sentiment_euphoric(self, analyst):
        """高涨幅+多涨停 → 亢奋"""
        assert analyst._determine_sentiment({"change_percent": 3.25, "limit_up_count": 15}) == "亢奋"

    def test_determine_sentiment_bullish(self, analyst):
        """正涨幅 → 平稳偏多"""
        assert analyst._determine_sentiment({"change_percent": 0.5, "limit_up_count": 5}) == "平稳偏多"

    def test_determine_sentiment_bearish(self, analyst):
        """小幅下跌 → 平稳偏空"""
        assert analyst._determine_sentiment({"change_percent": -1.0, "limit_up_count": 2}) == "平稳偏空"

    def test_determine_sentiment_panic(self, analyst):
        """大幅下跌 → 恐慌"""
        assert analyst._determine_sentiment({"change_percent": -3.5, "limit_up_count": 1}) == "恐慌"

    def test_determine_sentiment_invalid(self, analyst):
        """无效数据 → 平稳偏空（change_percent=0 不触发涨/跌，limit_up=0不触发亢奋）"""
        result = analyst._determine_sentiment({})
        assert "平稳" in result  # 包含平稳即可


class TestNewsAnalystMock:
    """新闻分析师模拟分析测试"""

    def test_calculate_sentiment_positive(self):
        from app.agents.news_analyst import NewsAnalyst
        agent = NewsAnalyst()
        data = {"articles": [{"sentiment": "正面"}, {"sentiment": "正面"}, {"sentiment": "中性"}]}
        score = agent._calculate_sentiment(data)
        assert score > 0.3

    def test_calculate_sentiment_negative(self):
        from app.agents.news_analyst import NewsAnalyst
        agent = NewsAnalyst()
        data = {"articles": [{"sentiment": "负面"}, {"sentiment": "负面"}, {"sentiment": "中性"}]}
        score = agent._calculate_sentiment(data)
        assert score < -0.3

    def test_calculate_sentiment_empty(self):
        from app.agents.news_analyst import NewsAnalyst
        agent = NewsAnalyst()
        assert agent._calculate_sentiment({}) == 0.0

    def test_mock_analysis_positive(self):
        from app.agents.news_analyst import NewsAnalyst
        agent = NewsAnalyst()
        data = {"articles": [{"sentiment": "正面", "title": "利好政策出台"}, {"sentiment": "正面", "title": "业绩超预期"}]}
        text = agent._mock_analysis(data)
        assert "积极" in text or "利好" in text

    def test_mock_analysis_negative(self):
        from app.agents.news_analyst import NewsAnalyst
        agent = NewsAnalyst()
        data = {"articles": [{"sentiment": "负面", "title": "业绩预警"}, {"sentiment": "负面", "title": "监管风险"}]}
        text = agent._mock_analysis(data)
        assert "消极" in text or "风险" in text


# ============================================================
# 4. TraderAgent 交易决策测试
# ============================================================

class TestTraderAgent:
    """交易决策 Agent 测试"""

    @pytest.fixture
    def agent(self):
        from app.agents.trader_agent import TraderAgent
        return TraderAgent()

    def test_decide_direction_buy(self, agent):
        """多方信号 → 买入"""
        reports = {
            "fa": {"analysis": "建议买入", "signal": "buy"},
            "ta": {"analysis": "看涨", "signal": "strong_buy"},
        }
        assert agent._decide_direction(reports) == "买入"

    def test_decide_direction_sell(self, agent):
        """空方信号 → 卖出"""
        reports = {
            "fa": {"analysis": "建议卖出", "signal": "sell"},
            "ta": {"analysis": "看跌", "signal": "strong_sell"},
        }
        assert agent._decide_direction(reports) == "卖出"

    def test_decide_direction_hold(self, agent):
        """中性信号 → 持有"""
        reports = {
            "fa": {"analysis": "中性", "signal": "neutral"},
            "ta": {"analysis": "持有观望", "signal": "neutral"},
        }
        assert agent._decide_direction(reports) == "持有"

    def test_calc_confidence_high(self, agent):
        """强信号 → 高置信度"""
        reports = {
            "ta": {"signal": "strong_buy"},
        }
        assert agent._calc_confidence(reports) >= 7

    def test_calc_confidence_low(self, agent):
        """中性信号 → 低置信度"""
        reports = {
            "ta": {"signal": "neutral"},
        }
        assert agent._calc_confidence(reports) <= 5

    def test_calc_confidence_default(self, agent):
        """无信号 → 默认置信度"""
        assert agent._calc_confidence({}) == 5

    def test_decide_position_sell(self, agent):
        """卖出方向 → 空仓"""
        assert "空仓" in agent._decide_position("卖出", 8, {})

    def test_decide_position_high_confidence(self, agent):
        """高置信度买入 → 重仓"""
        pos = agent._decide_position("买入", 9, {})
        assert "60" in pos or "80" in pos or "重仓" in pos

    def test_decide_position_low_confidence(self, agent):
        """低置信度买入 → 轻仓"""
        pos = agent._decide_position("买入", 5, {})
        assert "轻仓" in pos or "试探" in pos

    def test_calc_stop_loss_sell(self, agent):
        """卖出方向止损较紧"""
        assert "-3%" in agent._calc_stop_loss("卖出", 0.5)

    def test_calc_stop_loss_low_volatility(self, agent):
        """低波动率 → 较紧止损"""
        assert "-3%" in agent._calc_stop_loss("买入", 0.15)

    def test_calc_stop_loss_high_volatility(self, agent):
        """高波动率 → 较宽止损"""
        assert "-7%" in agent._calc_stop_loss("买入", 0.6)

    def test_calc_target_buy(self, agent):
        """买入目标基于波动率和置信度计算"""
        target = agent._calc_target(7, 0.3, "买入")
        assert "+" in target
        assert "%" in target

    def test_calc_target_sell(self, agent):
        """卖出方向返回止盈目标"""
        target = agent._calc_target(7, 0.3, "卖出")
        assert "-" in target

    def test_extract_signal_data(self, agent):
        """从报告中提取信号数据"""
        reports = {
            "technical_analyst": {
                "data": {"rsi": 65, "boll_up": 16, "boll_low": 14, "boll_mid": 15},
            },
            "sentiment_analyst": {"sentiment": "亢奋"},
        }
        data = agent._extract_signal_data(reports)
        assert data["rsi"] == 65
        assert data["volatility"] >= 0.5  # 亢奋+布林带宽调整

    def test_generate_reason(self, agent):
        """生成的理由包含方向建议"""
        reports = {
            "fa": {"analysis": "建议买入，估值合理"},
            "ta": {"analysis": "看涨，MACD金叉"},
        }
        reason = agent._generate_reason("买入", "30%仓位", reports)
        assert "买入" in reason
        assert "位" in reason


# ============================================================
# 5. RiskManager 风险评估测试
# ============================================================

class TestRiskManager:
    """风控 Agent 测试"""

    @pytest.fixture
    def rm(self):
        from app.agents.risk_manager import RiskManager
        return RiskManager()

    def test_assess_risk_low(self, rm):
        """高置信度 + 低波动率 → 低风险"""
        assert rm._assess_risk("买入", 9, 0.12) == "低"

    def test_assess_risk_high(self, rm):
        """低置信度 + 高波动率 → 高风险"""
        assert rm._assess_risk("买入", 3, 0.6) == "高"

    def test_assess_risk_sell_direction(self, rm):
        """卖出方向本身风险较低"""
        assert rm._assess_risk("卖出", 5, 0.35) == "中"

    def test_assess_risk_sell_low_vol(self, rm):
        """卖出+低波动→低风险"""
        assert rm._assess_risk("卖出", 5, 0.2) == "低"

    def test_extract_volatility_from_reports(self, rm):
        """从技术分析报告提取波动率"""
        reports = {
            "technical_analyst": {
                "data": {"boll_up": 16, "boll_low": 14, "close": 15},
            },
        }
        vol = rm._extract_volatility(reports)
        assert abs(vol - 0.133) < 0.01

    def test_extract_volatility_default(self, rm):
        """空报告返回默认波动率"""
        assert abs(rm._extract_volatility({}) - 0.25) < 0.01

    def test_suggest_modifications_high_vol(self, rm):
        """高波动率下建议降低仓位"""
        decision = {"direction": "买入", "position": "60%-80%重仓", "stop_loss": "-5%"}
        suggestions = rm._suggest_modifications(decision, 0.5, "高")
        assert len(suggestions) > 0

    def test_suggest_modifications_low_vol(self, rm):
        """低波动率下建议适度加仓"""
        decision = {"direction": "买入", "position": "20%-40%轻仓", "stop_loss": "-3%"}
        suggestions = rm._suggest_modifications(decision, 0.08, "低")
        assert len(suggestions) > 0

    def test_finalize_high_risk(self, rm):
        """高风险下调整仓位为低风险仓位"""
        decision = {"direction": "买入", "position": "60%-80%重仓", "stop_loss": "-5%"}
        result = rm._finalize(decision, 0.6, "高")
        assert "15%" in result["adjusted_position"]
        assert "⚠️" in result["risk_warning"]

    def test_finalize_low_risk(self, rm):
        """低风险下建议适度参与"""
        decision = {"direction": "买入", "position": "空仓或减仓至10%以下", "stop_loss": "-5%"}
        result = rm._finalize(decision, 0.12, "低")
        assert "20%" in result["adjusted_position"]
        assert "✅" in result["risk_warning"]


# ============================================================
# 6. ResearcherTeam 辩论测试
# ============================================================

class TestResearcherTeam:
    """研究员辩论团队测试"""

    @pytest.mark.asyncio
    async def test_debate_returns_structure(self):
        from app.agents.researcher_team import ResearcherTeam
        team = ResearcherTeam()
        result = await team.analyze({"stock_code": "000001", "debate_rounds": 2})
        assert "debate_rounds" in result
        assert result["debate_rounds"] == 2
        assert "debate_log" in result
        assert len(result["debate_log"]) == 2
        assert "conclusion" in result

    @pytest.mark.asyncio
    async def test_debate_log_has_bullish_and_bearish(self):
        from app.agents.researcher_team import ResearcherTeam
        team = ResearcherTeam()
        result = await team.analyze({"stock_code": "600519", "debate_rounds": 1})
        log_entry = result["debate_log"][0]
        assert "bullish" in log_entry or "round" in log_entry

    def test_format_debate_result_with_exception(self):
        from app.agents.researcher_team import ResearcherTeam
        result = ResearcherTeam._format_debate_result(ValueError("test"), "bullish")
        assert "失败" in result or "获取失败" in result

    def test_format_debate_result_with_string(self):
        from app.agents.researcher_team import ResearcherTeam
        assert ResearcherTeam._format_debate_result("看涨分析文本", "bullish") == "看涨分析文本"

    def test_format_debate_result_with_none(self):
        from app.agents.researcher_team import ResearcherTeam
        result = ResearcherTeam._format_debate_result(None, "bullish")
        assert "未提供" in result


# ============================================================
# 7. DialogueService 测试
# ============================================================

class TestDialogueService:
    """对话服务测试"""

    @pytest.mark.asyncio
    async def test_chat_no_stock_code(self):
        """无股票代码时正常回复"""
        svc = DialogueService()
        result = await svc.chat("你好，有什么推荐的股票吗？")
        assert "reply" in result
        assert len(result["reply"]) > 10

    @pytest.mark.asyncio
    async def test_chat_with_invalid_code(self):
        """无效股票代码时正常回复（不构建上下文）"""
        svc = DialogueService()
        result = await svc.chat("分析股票", "abc")
        assert "reply" in result

    @pytest.mark.asyncio
    async def test_chat_with_history(self):
        """带历史消息时正常回复"""
        svc = DialogueService()
        history = [{"role": "user", "content": "之前问过"}, {"role": "assistant", "content": "之前回答过"}]
        result = await svc.chat("继续分析", "", history)
        assert "reply" in result

    @pytest.mark.asyncio
    async def test_build_context_with_valid_code(self):
        """有效股票代码构建上下文"""
        svc = DialogueService()
        context = await svc._build_context("000001")
        assert "000001" in context

    @pytest.mark.asyncio
    async def test_build_context_empty_code(self):
        """空股票代码返回空上下文"""
        svc = DialogueService()
        assert await svc._build_context("") == ""

    @pytest.mark.asyncio
    async def test_build_context_invalid_code(self):
        """非6位数字代码返回空上下文"""
        svc = DialogueService()
        assert await svc._build_context("invalid") == ""
        assert await svc._build_context("12345") == ""

    @pytest.mark.asyncio
    async def test_chat_exception_graceful(self):
        """异常时返回友好的错误信息"""
        svc = DialogueService()
        with patch.object(svc, "_build_context", side_effect=RuntimeError("test error")):
            result = await svc.chat("分析")
        assert "reply" in result
        assert "抱歉" in result["reply"]


# ============================================================
# 8. MultiAgentService 多智能体编排测试
# ============================================================

class TestMultiAgentService:
    """多智能体编排引擎测试"""

    def test_init_creates_7_agents(self):
        svc = MultiAgentService()
        assert len(svc.agents) == 7

    def test_agent_names_are_unique(self):
        svc = MultiAgentService()
        names = [a.name for a in svc.agents]
        assert len(names) == len(set(names))
        assert "fundamentals_analyst" in names
        assert "technical_analyst" in names
        assert "sentiment_analyst" in names
        assert "news_analyst" in names
        assert "researcher_team" in names
        assert "trader_agent" in names
        assert "risk_manager" in names

    def test_find_agent_by_type(self):
        svc = MultiAgentService()
        from app.agents.trader_agent import TraderAgent
        from app.agents.risk_manager import RiskManager
        assert svc._find_agent(TraderAgent).name == "trader_agent"
        assert svc._find_agent(RiskManager).name == "risk_manager"

    @pytest.mark.asyncio
    async def test_analyze_stock_returns_full_structure(self):
        svc = MultiAgentService()
        result = await svc.analyze_stock("000001")
        assert result["stock_code"] == "000001"
        assert "reports" in result
        assert "fused_decision" in result
        assert len(result["reports"]) == 7

    @pytest.mark.asyncio
    async def test_analyze_stock_each_agent_has_analysis(self):
        svc = MultiAgentService()
        result = await svc.analyze_stock("000001")
        for name, report in result["reports"].items():
            assert report is not None
            if isinstance(report, dict):
                assert any(k in report for k in (
                    "agent", "view", "status", "conclusion", "debate_log",
                    "direction", "confidence", "risk_level",
                ))
                # 检查 mock mode 下 agent name 一致性
                if "agent" in report:
                    assert report["agent"] == name

    @pytest.mark.asyncio
    async def test_analyze_all_multiple_stocks(self):
        svc = MultiAgentService()
        result = await svc.analyze_all(["000001", "600519"])
        assert len(result) == 2
        assert "000001" in result
        assert "600519" in result

    @pytest.mark.asyncio
    async def test_iterative_debate(self):
        svc = MultiAgentService()
        result = await svc.iterative_debate("000001", rounds=2)
        assert result["debate_rounds"] == 2
        assert len(result["debate_log"]) == 2

    def test_custom_agents(self):
        from app.agents.fundamentals_analyst import FundamentalsAnalyst
        svc = MultiAgentService(agents=[FundamentalsAnalyst()])
        assert len(svc.agents) == 1

    def test_timeout_default(self):
        svc = MultiAgentService()
        assert svc.timeout == 30


# ============================================================
# 9. SimulationEngine 模拟引擎测试
# ============================================================

class TestSimulationEngineExtended:
    """模拟引擎扩展测试"""

    def test_all_agent_templates_format_correctly(self):
        data = get_mock_data()
        data["stock_code"] = "000001"
        for role, templates in AGENT_TEMPLATES.items():
            for sentiment, template in templates.items():
                try:
                    result = template.format(**data)
                    assert len(result) > 10
                except KeyError as e:
                    pytest.fail(f"Agent 模板 {role}/{sentiment} 缺少占位符: {e}")

    def test_all_dialog_templates_format_correctly(self):
        data = get_mock_data("测试")
        for key, template in DIALOG_TEMPLATES.items():
            try:
                result = template.format(**data)
                assert len(result) > 10
            except KeyError as e:
                pytest.fail(f"对话模板 {key} 缺少占位符: {e}")

    def test_simulation_for_each_agent_role(self):
        roles = ["fundamentals_analyst", "technical_analyst", "sentiment_analyst",
                 "news_analyst", "trader_agent", "risk_manager"]
        for role in roles:
            result = SimulationEngine.get_simulation(role, {"stock_code": "000001"})
            assert isinstance(result, str)
            assert len(result) > 10

    def test_simulation_with_context_overrides(self):
        result = SimulationEngine.get_simulation("trader_agent", {
            "stock_code": "000001", "direction": "买入", "confidence": 8,
        })
        assert "000001" in result or "买入" in result

    def test_simulation_fallback_on_format_error(self):
        result = SimulationEngine.get_simulation("fundamentals_analyst", {"unexpected_key": "x"})
        assert isinstance(result, str)


# ============================================================
# 10. API 路由请求校验测试
# ============================================================

class TestAPIRequestValidation:
    """API 请求体 Pydantic 校验测试"""

    def test_chat_request_valid(self):
        from app.api.dialogue import ChatRequest
        req = ChatRequest(message="分析000001", stock_code="000001")
        assert req.message == "分析000001"
        assert req.stock_code == "000001"

    def test_chat_request_empty_message(self):
        from app.api.dialogue import ChatRequest
        with pytest.raises(ValueError, match="不能为空"):
            ChatRequest(message="")

    def test_chat_request_message_too_long(self):
        from app.api.dialogue import ChatRequest
        with pytest.raises(ValueError, match="不能超过"):
            ChatRequest(message="x" * 2001)

    def test_chat_request_invalid_stock_code(self):
        from app.api.dialogue import ChatRequest
        with pytest.raises(ValueError, match="格式错误"):
            ChatRequest(message="分析", stock_code="123")

    def test_chat_request_invalid_history_type(self):
        from app.api.dialogue import ChatRequest
        with pytest.raises(ValueError):
            ChatRequest(message="分析", history="not_a_list")

    def test_chat_request_history_missing_fields(self):
        from app.api.dialogue import ChatRequest
        with pytest.raises(ValueError, match="缺少"):
            ChatRequest(message="分析", history=[{"role": "user"}])

    def test_chat_request_history_too_long(self):
        from app.api.dialogue import ChatRequest
        with pytest.raises(ValueError, match="不能超过"):
            ChatRequest(message="分析", history=[{"role": "user", "content": "x"} for _ in range(51)])

    def test_analyze_request_valid(self):
        from app.api.dialogue import AnalyzeRequest
        req = AnalyzeRequest(stock_code="000001")
        assert req.stock_code == "000001"

    def test_analyze_request_invalid_code(self):
        from app.api.dialogue import AnalyzeRequest
        with pytest.raises(ValueError, match="格式错误"):
            AnalyzeRequest(stock_code="123")

    def test_analyze_request_empty_code(self):
        from app.api.dialogue import AnalyzeRequest
        with pytest.raises(ValueError):
            AnalyzeRequest(stock_code="")

    def test_debate_request_valid(self):
        from app.api.dialogue import DebateRequest
        req = DebateRequest(stock_code="000001", rounds=3)
        assert req.rounds == 3

    def test_debate_request_rounds_out_of_range(self):
        from app.api.dialogue import DebateRequest
        with pytest.raises(ValueError):
            DebateRequest(stock_code="000001", rounds=0)
        with pytest.raises(ValueError):
            DebateRequest(stock_code="000001", rounds=11)


# ============================================================
# 11. ModelRegistry 模型注册表测试
# ============================================================

class TestModelRegistry:
    """模型注册表测试"""

    def test_list_models(self):
        models = ModelRegistry.list_models()
        assert len(models) >= 3
        assert "deepseek-chat" in models

    def test_get_client_default(self):
        client = ModelRegistry.get_client()
        assert client is not None
        assert hasattr(client, "chat")

    def test_get_client_with_api_key(self):
        client = ModelRegistry.get_client("deepseek", "sk-test")
        assert client is not None
        assert hasattr(client, "model")
        assert hasattr(client, "chat")

    def test_get_client_caching(self):
        client1 = ModelRegistry.get_client("deepseek", "sk-test")
        client2 = ModelRegistry.get_client("deepseek", "sk-test")
        assert client1 is client2

    def test_health_check(self):
        status = ModelRegistry.health_check()
        assert isinstance(status, dict)


# ============================================================
# 12. MemoryService 记忆服务扩展测试
# ============================================================

class TestMemoryServiceExtended:
    """记忆服务扩展测试"""

    @pytest.fixture
    def mem(self):
        svc = MemoryService()
        test_file = svc.MEMORY_DIR / "test_cleanup.json"
        if test_file.exists():
            test_file.unlink()
        return svc

    def test_init_creates_dir(self, mem):
        assert mem.MEMORY_DIR.exists()

    def test_load_history_empty(self, mem):
        history = asyncio.run(mem.load_history("NONEXIST"))
        assert history == []

    def test_save_and_load_decision(self, mem):
        code = "TEST888"
        test_file = mem.MEMORY_DIR / f"{code}.json"
        if test_file.exists():
            test_file.unlink()

        decision = {"direction": "买入", "confidence": 7}
        path = asyncio.run(mem.save_decision(code, decision))
        assert isinstance(path, str)

        history = asyncio.run(mem.load_history(code))
        assert len(history) == 1
        assert history[0]["decision"]["direction"] == "买入"

        # 清理
        if test_file.exists():
            test_file.unlink()

    def test_auto_reflect_insufficient(self, mem):
        result = asyncio.run(mem.auto_reflect("NONEXIST"))
        assert "暂无足够" in result["message"]

    def test_get_all_stocks(self, mem):
        stocks = asyncio.run(mem.get_all_stocks())
        assert isinstance(stocks, list)

    def test_max_history_limit(self, mem):
        code = "TESTMAX"
        test_file = mem.MEMORY_DIR / f"{code}.json"
        if test_file.exists():
            test_file.unlink()

        # 保存超出上限的记录
        for i in range(110):
            asyncio.run(mem.save_decision(code, {"direction": f"test_{i}"}))

        history = asyncio.run(mem.load_history(code))
        assert len(history) <= 100

        # 清理
        if test_file.exists():
            test_file.unlink()


# ============================================================
# 13. 配置验证测试
# ============================================================

class TestConfig:
    """配置层测试"""

    def test_settings_load(self):
        assert hasattr(settings, "log_level")
        assert hasattr(settings, "deepseek_api_key")
        assert hasattr(settings, "backend_api_url")
        assert hasattr(settings, "deepseek_model")
        assert settings.deepseek_model == "deepseek-chat"

    def test_backend_api_url_format(self):
        assert settings.backend_api_url.endswith("/api")

    def test_siliconflow_config_exists(self):
        assert hasattr(settings, "siliconflow_api_key")
        assert hasattr(settings, "siliconflow_api_url")
        assert hasattr(settings, "siliconflow_model")

    def test_redis_config(self):
        assert hasattr(settings, "redis_host")
        assert hasattr(settings, "redis_port")
        assert settings.redis_port == 6379

    def test_log_level_valid(self):
        assert settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR")

    def test_default_api_key_empty(self):
        # 确保默认无 API Key 时自动模拟降级
        assert settings.deepseek_api_key == ""
