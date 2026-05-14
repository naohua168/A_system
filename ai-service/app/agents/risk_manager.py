"""风控经理 Agent — 评估交易决策风险"""
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.models.deepseek_client import AIClient


class RiskManager(BaseAgent):
    """风控经理：评估并批准/拒绝/修改交易决策"""

    def __init__(self, model_client: Optional[AIClient] = None):
        super().__init__(
            name="risk_manager",
            role="风控经理",
            system_prompt="你是一名严格的风控经理，负责评估交易决策的风险并做出最终裁定。",
            model_client=model_client,
        )

    async def analyze(self, context: dict) -> dict:
        decision = context.get("trade_decision", {})
        direction = decision.get("direction", "")
        confidence = decision.get("confidence", 0)
        position = decision.get("position", "")

        assessment = {
            "status": "approved",
            "risk_level": self._assess_risk(direction, confidence),
            "modifications": self._suggest_modifications(decision),
            "final_decision": self._finalize(decision),
        }
        return assessment

    def _assess_risk(self, direction: str, confidence: int) -> str:
        if confidence < 5:
            return "高"
        elif confidence < 7:
            return "中"
        return "低"

    def _suggest_modifications(self, decision: dict) -> list:
        suggestions = []
        if decision.get("position", "").startswith("50"):
            suggestions.append("建议降低仓位至30%")
        if decision.get("stop_loss", "") == "-3%":
            suggestions.append("建议放宽止损至-5%")
        return suggestions

    def _finalize(self, decision: dict) -> dict:
        return {
            "action": decision.get("direction", "持有"),
            "adjusted_position": "20%仓位",
            "stop_loss": "-5%",
            "risk_warning": "市场有风险，投资需谨慎。本决策仅供参考。"
        }

    def _mock_reply(self, messages) -> str:
        return (
            "**风险评估报告**\n\n"
            "决策审核：✅ 已批准\n"
            "风险等级：中等\n"
            "调整建议：建议将仓位从30%降低至20%\n"
            "止损位：-5%（不变）\n\n"
            "⚠️ 风控提示：当前市场波动较大，建议分批建仓，"
            "首次建仓后观察1-2个交易日再决定是否加仓。"
        )
