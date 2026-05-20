"""多智能体编排引擎 — 协调多个Agent协作分析 + Fusion融合"""
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
from app.fusion import fusion_engine


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

        流程:
        1. 并行执行所有 Agent 分析（asyncio.gather）
        2. 将分析结果注入 TraderAgent 和 RiskManager 作为上下文
        3. 通过 FusionEngine 加权投票融合
        4. 返回 Agent 原始报告 + 融合决策
        """
        context = {"stock_code": stock_code}
        timeout_per_agent = self.timeout

        # ── 阶段1: 并行执行独立 Agent（基本面/技术/情绪/新闻/辩论） ──
        independent_agents = [a for a in self.agents
                              if not isinstance(a, (TraderAgent, RiskManager))]

        async def run_agent(agent):
            try:
                result = await asyncio.wait_for(
                    agent.analyze(context), timeout=timeout_per_agent
                )
                return agent.name, result
            except asyncio.TimeoutError:
                logger.warning(f"[{agent.name}] 超时")
                return agent.name, {"error": "timeout", "status": "failed", "analysis": "", "agent": agent.name}
            except Exception as e:
                logger.error(f"[{agent.name}] 失败: {e}")
                return agent.name, {"error": str(e), "status": "failed", "analysis": "", "agent": agent.name}

        results_list = await asyncio.gather(*[run_agent(a) for a in independent_agents])
        reports = dict(results_list)

        # ── 阶段2: 注入报告到 TraderAgent 和 RiskManager ──
        trader_context = {**context, "agent_reports": reports}
        trader_result = await run_agent(self._find_agent(TraderAgent))
        reports[trader_result[0]] = trader_result[1]

        risk_context = {**context, "trade_decision": trader_result[1] if not isinstance(trader_result[1].get("error"), str) else {}}
        risk_result = await run_agent(self._find_agent(RiskManager))
        reports[risk_result[0]] = risk_result[1]

        # ── 阶段3: FusionEngine 融合 ──
        try:
            fused = fusion_engine.fuse(reports)
            fused["stock_code"] = stock_code
        except Exception as e:
            logger.error(f"融合失败: {e}")
            fused = {"action": "hold", "confidence": 0, "reason": f"融合异常: {e}"}

        return {
            "stock_code": stock_code,
            "reports": reports,
            "fused_decision": fused,
        }

    def _find_agent(self, agent_type) -> BaseAgent:
        """按类型查找 Agent 实例"""
        for agent in self.agents:
            if isinstance(agent, agent_type):
                return agent
        raise ValueError(f"未找到 {agent_type.__name__} 实例")

    async def analyze_all(self, codes: list[str] = None) -> dict:
        """批量分析多个股票"""
        if codes is None:
            codes = ["000001", "600519", "300750"]
        stock_tasks = [self.analyze_stock(code) for code in codes]
        results_list = await asyncio.gather(*stock_tasks)
        return {r["stock_code"]: r for r in results_list}

    async def iterative_debate(self, stock_code: str, rounds: int = 3) -> dict:
        """迭代辩论分析"""
        for agent in self.agents:
            if isinstance(agent, ResearcherTeam):
                return await agent.analyze({
                    "stock_code": stock_code, "debate_rounds": rounds,
                })
        return {"error": "未找到研究员辩论Agent"}


multi_agent_service = MultiAgentService()
