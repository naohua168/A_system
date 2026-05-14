"""交易员 Agent — 综合报告生成交易决策"""
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.models.deepseek_client import AIClient


class TraderAgent(BaseAgent):
    """交易员：综合各Agent报告生成最终交易决策"""

    def __init__(self, model_client: Optional[AIClient] = None):
        super().__init__(
            name="trader_agent",
            role="交易员",
            system_prompt="你是一名资深交易员，综合基本面、技术面、情绪面信息做出交易决策。",
            model_client=model_client,
        )

    async def analyze(self, context: dict) -> dict:
        stock_code = context.get("stock_code", "")
        reports = context.get("agent_reports", {})

        decision = {
            "stock_code": stock_code,
            "direction": self._decide_direction(reports),
            "position": self._decide_position(reports),
            "stop_loss": self._calc_stop_loss(reports),
            "target": self._calc_target(reports),
            "reason": self._generate_reason(reports),
            "confidence": self._calc_confidence(reports),
        }
        return decision

    def _decide_direction(self, reports: dict) -> str:
        bullish_score = 0
        for r in reports.values():
            if isinstance(r, dict):
                text = str(r.get("conclusion", r.get("analysis", "")))
                if "买入" in text or "看涨" in text or "推荐" in text:
                    bullish_score += 1
                elif "卖出" in text or "看跌" in text or "回避" in text:
                    bullish_score -= 1
        if bullish_score > 1:
            return "买入"
        elif bullish_score < -1:
            return "卖出"
        return "持有"

    def _decide_position(self, reports: dict) -> str:
        return "30%仓位"

    def _calc_stop_loss(self, reports: dict) -> str:
        return "-5%"

    def _calc_target(self, reports: dict) -> str:
        return "+10%"

    def _generate_reason(self, reports: dict) -> str:
        return "综合多维度分析，当前操作建议"

    def _calc_confidence(self, reports: dict) -> int:
        return 7

    def _mock_reply(self, messages) -> str:
        return (
            "**交易决策报告**\n\n"
            "方向：买入\n"
            "仓位：30%（轻仓试探）\n"
            "止损位：-5%\n"
            "目标位：+10%\n"
            "信心指数：7/10\n\n"
            "理由：基本面估值合理，技术面短期多头，"
            "资金面有主力介入迹象。建议分批建仓。"
        )
