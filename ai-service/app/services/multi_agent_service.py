"""多智能体编排引擎 — 协调多个Agent协作分析"""
import asyncio
from typing import Optional

from loguru import logger

from app.agents.base_agent import BaseAgent
from app.agents.fundamentals_analyst import FundamentalsAnalyst
from app.agents.technical_analyst import TechnicalAnalyst
from app.agents.sentiment_analyst import SentimentAnalyst
from app.agents.news_analyst import NewsAnalyst
from app.agents.researcher_team import ResearcherTeam
from app.agents.trader_agent import TraderAgent
from app.agents.risk_manager import RiskManager


class MultiAgentService:
    """多智能体编排引擎"""

    def __init__(self, agents: Optional[list[BaseAgent]] = None):
        self.agents = agents or [
            FundamentalsAnalyst(),
            TechnicalAnalyst(),
            SentimentAnalyst(),
            NewsAnalyst(),
            ResearcherTeam(),
            TraderAgent(),
            RiskManager(),
        ]
        self.timeout = 30

    async def analyze_stock(self, stock_code: str) -> dict:
        """分析单个股票"""
        context = {"stock_code": stock_code}
        reports = {}

        for agent in self.agents:
            try:
                result = await asyncio.wait_for(
                    agent.analyze(context),
                    timeout=self.timeout / len(self.agents)
                )
                reports[agent.name] = result
            except asyncio.TimeoutError:
                reports[agent.name] = {"error": "timeout", "status": "failed"}
            except Exception as e:
                logger.error(f"[{agent.name}] 失败: {e}")
                reports[agent.name] = {"error": str(e), "status": "failed"}

        return {"stock_code": stock_code, "reports": reports}

    async def analyze_all(self, codes: list[str] = None) -> dict:
        if codes is None:
            codes = ["000001", "600519", "300750"]
        results = {}
        for code in codes:
            results[code] = await self.analyze_stock(code)
        return results

    async def iterative_debate(self, stock_code: str, rounds: int = 3) -> dict:
        for agent in self.agents:
            if isinstance(agent, ResearcherTeam):
                return await agent.analyze({
                    "stock_code": stock_code, "debate_rounds": rounds,
                })
        return {"error": "未找到研究员辩论Agent"}


multi_agent_service = MultiAgentService()
