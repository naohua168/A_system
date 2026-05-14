"""AI服务测试的共享fixture"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pytest
from app.agents.base_agent import BaseAgent
from app.agents.fundamentals_analyst import FundamentalsAnalyst
from app.agents.technical_analyst import TechnicalAnalyst
from app.agents.sentiment_analyst import SentimentAnalyst
from app.agents.news_analyst import NewsAnalyst
from app.agents.researcher_team import ResearcherTeam
from app.agents.trader_agent import TraderAgent
from app.agents.risk_manager import RiskManager
from app.models.deepseek_client import AIClient
from app.models.simulation import SimulationEngine
from app.services.memory_service import MemoryService


@pytest.fixture
def fundamentals_analyst():
    return FundamentalsAnalyst()


@pytest.fixture
def technical_analyst():
    return TechnicalAnalyst()


@pytest.fixture
def sentiment_analyst():
    return SentimentAnalyst()


@pytest.fixture
def trader_agent():
    return TraderAgent()


@pytest.fixture
def risk_manager():
    return RiskManager()


@pytest.fixture
def memory_service():
    return MemoryService()


@pytest.fixture
def mock_context():
    return {
        "stock_code": "000001",
        "sentiment": "bullish",
        "debate_rounds": 2,
        "agent_reports": {
            "fundamentals_analyst": {"conclusion": "基本面良好，建议买入"},
            "technical_analyst": {"conclusion": "技术面看涨"},
            "trader_agent": {"direction": "买入", "confidence": 7, "position": "30%仓位", "stop_loss": "-5%"},
        },
        "trade_decision": {"direction": "买入", "confidence": 7, "position": "30%仓位", "stop_loss": "-5%"},
    }
