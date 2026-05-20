"""风控经理 Agent — 评估交易决策风险，引入市场波动率评估"""
import math
from typing import Optional

from loguru import logger

from app.agents.base_agent import BaseAgent
from app.models.deepseek_client import AIClient


class RiskManager(BaseAgent):
    """风控经理：评估并批准/拒绝/修改交易决策"""

    # 波动率对应的风险等级
    VOLATILITY_RISK_MAP = [
        (0.15, "低"),   # 波动率 ≤ 15%
        (0.25, "较低"),
        (0.35, "中"),
        (0.50, "较高"),
        (1.0,  "高"),   # 波动率 > 50%
    ]

    def __init__(self, model_client: Optional[AIClient] = None):
        super().__init__(
            name="risk_manager",
            role="风控经理",
            system_prompt="你是一名严格的风控经理，负责综合市场波动率、置信度和仓位评估交易决策风险。",
            model_client=model_client,
        )

    async def analyze(self, context: dict) -> dict:
        decision = context.get("trade_decision", {})
        reports = context.get("agent_reports", {})

        # 从各 Agent 报告中提取波动率数据
        volatility = self._extract_volatility(reports)
        direction = decision.get("direction", "")
        confidence = decision.get("confidence", 0)
        position = decision.get("position", "")

        risk_level = self._assess_risk(direction, confidence, volatility)
        modifications = self._suggest_modifications(decision, volatility, risk_level)
        final_decision = self._finalize(decision, volatility, risk_level)

        assessment = {
            "status": "approved" if risk_level not in ("高",) else "conditional",
            "risk_level": risk_level,
            "volatility": round(volatility, 3),
            "modifications": modifications,
            "final_decision": final_decision,
        }
        return assessment

    def _extract_volatility(self, reports: dict) -> float:
        """从各 Agent 报告中提取市场波动率"""
        # 默认中等波动率
        vol = 0.25

        for name, report in reports.items():
            if not isinstance(report, dict):
                continue

            # 从技术分析获取布林带宽作为波动率
            if name == "technical_analyst":
                tech_data = report.get("data", {})
                try:
                    boll_up = float(tech_data.get("boll_up", 0))
                    boll_low = float(tech_data.get("boll_low", 0))
                    close = float(tech_data.get("close", 1))
                    if close > 0 and boll_up > boll_low:
                        vol = (boll_up - boll_low) / close
                except (ValueError, TypeError):
                    pass

            # 从情绪分析获取情绪波动
            elif name == "sentiment_analyst":
                sentiment = report.get("sentiment", "")
                if sentiment == "亢奋":
                    vol = max(vol, 0.35)
                elif sentiment == "恐慌":
                    vol = max(vol, 0.45)
                elif "平稳" in sentiment:
                    vol = min(vol, 0.20)

            # 从交易决策获取 volatility 字段
            elif name == "trader_agent":
                vol_from_trader = report.get("volatility", 0)
                if vol_from_trader > 0:
                    vol = max(vol, vol_from_trader)

        return min(max(vol, 0.05), 0.8)  # 限制在 5%-80% 范围

    def _assess_risk(self, direction: str, confidence: int, volatility: float) -> str:
        """综合评估风险等级（置信度 + 波动率）"""
        if direction == "卖出":
            # 卖出操作本身风险较低
            if volatility < 0.3:
                return "低"
            return "中"

        # 置信度评分 (0-10 → 0-1)
        conf_score = confidence / 10.0

        # 综合风险: 波动率占 60%，置信度反转占 40%
        risk_score = volatility * 0.6 + (1 - conf_score) * 0.4

        for threshold, level in self.VOLATILITY_RISK_MAP:
            if risk_score <= threshold:
                return level
        return "高"

    def _suggest_modifications(self, decision: dict, volatility: float, risk_level: str) -> list:
        """基于波动率和风险等级给出调整建议"""
        suggestions = []

        position = decision.get("position", "")
        stop_loss = decision.get("stop_loss", "")
        direction = decision.get("direction", "")

        # 高波动率下调整仓位
        if volatility > 0.4:
            suggestions.append(f"⚠️ 当前市场波动率较高({volatility*100:.0f}%)，建议降低仓位")
        elif volatility < 0.1:
            suggestions.append(f"✅ 市场波动率较低({volatility*100:.0f}%)，可适度加仓")

        # 高风险的仓位调整
        if risk_level == "高" and direction == "买入":
            suggestions.append("风险等级为高，建议仓位不超过15%或暂缓操作")

        # 止损检查
        if stop_loss and stop_loss in ("-3%", "-4%") and volatility > 0.3:
            suggestions.append(f"波动率{volatility*100:.0f}%，建议放宽止损至-7%以避免被震荡出局")
        elif stop_loss and stop_loss in ("-10%",) and volatility < 0.15:
            suggestions.append(f"波动率仅{volatility*100:.0f}%，止损-10%过宽，建议收紧至-5%")

        # 仓位字符串检测
        if position and "60" in position and risk_level in ("较高", "高"):
            suggestions.append("风险等级较高，建议降低仓位至40%以下")
        elif position and ("80" in position or "重仓" in position) and volatility > 0.35:
            suggestions.append("高波动率环境下不建议重仓，建议降至50%以下")

        return suggestions

    def _finalize(self, decision: dict, volatility: float, risk_level: str) -> dict:
        """生成最终裁定"""
        direction = decision.get("direction", "持有")
        position = decision.get("position", "轻仓")
        stop_loss = decision.get("stop_loss", "-5%")

        # 根据风险等级调整最终仓位
        adjusted_position = position
        if risk_level == "高":
            adjusted_position = "不超过15%仓位（低风险仓位）"
        elif risk_level == "较高":
            if "重仓" in position or "60" in position:
                adjusted_position = "30%-40%仓位（适度降低）"
        elif risk_level == "低":
            if "空仓" in position or "10%" in position:
                adjusted_position = "20%-30%仓位（可适度参与）"

        return {
            "action": direction,
            "adjusted_position": adjusted_position,
            "stop_loss": stop_loss,
            "volatility": round(volatility, 3),
            "risk_level": risk_level,
            "risk_warning": (
                "⚠️ 高度风险：市场波动剧烈，建议仅以极小仓位参与或观望" if risk_level == "高"
                else "⚠️ 注意风险：市场存在不确定性，严格执行止损纪律" if risk_level in ("较高", "中")
                else "✅ 风险可控：当前市场环境相对稳定，可按计划执行"
            ),
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
