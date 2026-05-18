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
        """分析单个股票

        修复: 使用 asyncio.gather 并行执行所有 Agent 分析。
        各 Agent 之间无数据依赖，并行后总耗时降至最慢的一个 Agent。
        """
        context = {"stock_code": stock_code}
        timeout_per_agent = self.timeout

        async def run_agent(agent):
            try:
                result = await asyncio.wait_for(
                    agent.analyze(context), timeout=timeout_per_agent
                )
                return agent.name, result
            except asyncio.TimeoutError:
                return agent.name, {"error": "timeout", "status": "failed"}
            except Exception as e:
                logger.error(f"[{agent.name}] 失败: {e}")
                return agent.name, {"error": str(e), "status": "failed"}

        results_list = await asyncio.gather(*[run_agent(a) for a in self.agents])
        return {"stock_code": stock_code, "reports": dict(results_list)}

    async def analyze_all(self, codes: list[str] = None) -> dict:
        if codes is None:
            codes = ["000001", "600519", "300750"]
        # 修复: 并行分析多个股票
        stock_tasks = [self.analyze_stock(code) for code in codes]
        results_list = await asyncio.gather(*stock_tasks)
        return {r["stock_code"]: r for r in results_list}

    async def iterative_debate(self, stock_code: str, rounds: int = 3) -> dict:
        for agent in self.agents:
            if isinstance(agent, ResearcherTeam):
                return await agent.analyze({
                    "stock_code": stock_code, "debate_rounds": rounds,
                })
        return {"error": "未找到研究员辩论Agent"}


multi_agent_service = MultiAgentService()
