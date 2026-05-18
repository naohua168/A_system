"""多智能体融合引擎 — 加权投票聚合各 Agent 分析结果"""
from loguru import logger


class FusionEngine:
    """多智能体融合引擎

    对多个 Agent 的分析结果进行加权投票，生成最终决策建议。
    权重策略可根据历史准确率动态调整。
    """

    # 默认 Agent 权重
    DEFAULT_WEIGHTS = {
        "technical_analyst": 0.25,
        "fundamentals_analyst": 0.20,
        "sentiment_analyst": 0.15,
        "news_analyst": 0.15,
        "researcher_team": 0.15,
        "trader_agent": 0.05,
        "risk_manager": 0.05,
    }

    def __init__(self, weights: dict[str, float] | None = None):
        self._weights = weights or dict(self.DEFAULT_WEIGHTS)
        # 归一化权重
        total = sum(self._weights.values())
        if total > 0:
            self._weights = {k: v / total for k, v in self._weights.items()}

    def fuse(self, reports: dict[str, dict]) -> dict:
        """融合多个 Agent 的报告，输出最终决策

        Args:
            reports: {agent_name: {agent, role, stock_code, analysis, sentiment_score, ...}}
        Returns:
            融合后的决策结果
        """
        if not reports:
            return {"action": "hold", "confidence": 0, "reason": "无可用分析数据"}

        # 提取每个 Agent 的方向和置信度
        directions = []
        scores = []
        details = []

        for agent_name, report in reports.items():
            weight = self._weights.get(agent_name, 0.1)
            direction = self._extract_direction(report)
            confidence = self._extract_confidence(report)

            directions.append(direction)
            scores.append(confidence * weight)

            details.append({
                "agent": agent_name,
                "direction": direction,
                "confidence": confidence,
                "weight": round(weight, 3),
                "weighted_score": round(confidence * weight, 3),
            })

        # 加权投票
        buy_score = sum(s for d, s in zip(directions, scores) if d == "buy")
        sell_score = sum(s for d, s in zip(directions, scores) if d == "sell")
        hold_score = sum(s for d, s in zip(directions, scores) if d == "hold")

        if buy_score > max(sell_score, hold_score):
            final_action = "buy"
            final_confidence = buy_score / sum(self._weights.values())
        elif sell_score > hold_score:
            final_action = "sell"
            final_confidence = sell_score / sum(self._weights.values())
        else:
            final_action = "hold"
            final_confidence = hold_score / sum(self._weights.values())

        return {
            "action": final_action,
            "confidence": round(min(final_confidence, 1.0), 4),
            "buy_score": round(buy_score, 4),
            "sell_score": round(sell_score, 4),
            "hold_score": round(hold_score, 4),
            "agent_details": sorted(details, key=lambda x: x["weighted_score"], reverse=True),
            "stock_code": reports.get(list(reports.keys())[0], {}).get("stock_code", ""),
        }

    def update_weight(self, agent_name: str, new_weight: float):
        """动态更新某个 Agent 的权重"""
        if agent_name in self._weights:
            self._weights[agent_name] = new_weight
            total = sum(self._weights.values())
            self._weights = {k: v / total for k, v in self._weights.items()}
            logger.info(f"融合引擎: 更新 {agent_name} 权重为 {new_weight:.3f}")

    @staticmethod
    def _extract_direction(report: dict) -> str:
        """从 Agent 报告中提取操作方向"""
        decision = report.get("decision", {})
        direction = decision.get("direction", "")
        if direction in ("buy", "sell", "hold"):
            return direction
        # 从分析文本中推断
        analysis = (report.get("analysis") or "").lower()
        if any(kw in analysis for kw in ("买入", "看多", "增持", "recommend_buy")):
            return "buy"
        if any(kw in analysis for kw in ("卖出", "看空", "减持", "recommend_sell")):
            return "sell"
        return "hold"

    @staticmethod
    def _extract_confidence(report: dict) -> float:
        """从报告中提取置信度 (0~1)"""
        decision = report.get("decision", {})
        confidence = decision.get("confidence", 0.5)
        sentiment = abs(report.get("sentiment_score", 0))
        return min((confidence + sentiment) / 2, 1.0)


fusion_engine = FusionEngine()
