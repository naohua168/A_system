"""交易员 Agent — 动态计算交易决策（仓位/止损/目标基于数据）"""
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.models.deepseek_client import AIClient


class TraderAgent(BaseAgent):
    """交易员：综合各Agent报告生成最终交易决策，动态计算仓位/止损/目标"""

    # 仓位档位配置
    POSITION_TIERS = [
        (5, "60%-80%重仓"),   # 明确强烈买入信号 + 高置信度
        (3, "40%-60%中仓"),   # 较强买入信号
        (1, "20%-40%轻仓"),   # 温和买入信号
        (-1, "10%-20%试探仓"),# 偏空但有机会
        (-3, "空仓观望"),     # 明确卖出信号
    ]

    # 止损档位（基于波动率调整）
    STOP_LOSS_TIERS = [
        (0.3, "-3%"),   # 低波动率
        (0.5, "-5%"),   # 中等波动率
        (0.7, "-7%"),   # 高波动率
        (1.0, "-10%"),  # 极高波动率
    ]

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

        # 从各Agent报告中提取数据用于动态计算
        signal_data = self._extract_signal_data(reports)
        volatility = signal_data.get("volatility", 0.5)

        direction = self._decide_direction(reports)
        confidence = self._calc_confidence(reports)
        position = self._decide_position(direction, confidence, reports)
        stop_loss_pct = self._calc_stop_loss(direction, volatility)
        target_pct = self._calc_target(confidence, volatility, direction)
        reason = self._generate_reason(direction, position, reports)

        decision = {
            "stock_code": stock_code,
            "direction": direction,
            "position": position,
            "stop_loss": stop_loss_pct,
            "target": target_pct,
            "reason": reason,
            "confidence": confidence,
            "volatility": round(volatility, 2),
        }
        return decision

    def _extract_signal_data(self, reports: dict) -> dict:
        """从各Agent报告中提取信号数据用于动态计算"""
        data = {"volatility": 0.5, "rsi": 50, "boll_width": 0}
        for name, report in reports.items():
            if isinstance(report, dict):
                # 技术分析师的数据
                if name == "technical_analyst":
                    tech = report.get("data", {})
                    rsi = tech.get("rsi", 50)
                    try:
                        boll_up = float(tech.get("boll_up", 0))
                        boll_low = float(tech.get("boll_low", 0))
                        boll_mid = float(tech.get("boll_mid", 1))
                        if boll_mid > 0:
                            data["boll_width"] = (boll_up - boll_low) / boll_mid
                    except (ValueError, TypeError):
                        pass
                    try:
                        data["rsi"] = float(rsi)
                    except (ValueError, TypeError):
                        pass
                # 情绪分析师的波动率
                elif name == "sentiment_analyst":
                    sentiment = report.get("sentiment", "")
                    if sentiment == "亢奋":
                        data["volatility"] = 0.8
                    elif sentiment == "恐慌":
                        data["volatility"] = 0.9
                    elif "平稳" in sentiment:
                        data["volatility"] = 0.4
        # 结合布林带宽调整波动率
        bw = data.get("boll_width", 0)
        if bw > 0.15:
            data["volatility"] = min(data["volatility"] + 0.2, 1.0)
        elif bw < 0.05:
            data["volatility"] = max(data["volatility"] - 0.1, 0.1)
        return data

    def _decide_direction(self, reports: dict) -> str:
        """基于各Agent分析文本决定方向"""
        bullish_score = 0
        for r in reports.values():
            if isinstance(r, dict):
                text = str(r.get("conclusion", r.get("analysis", ""))).lower()
                if "买入" in text or "看涨" in text or "推荐" in text or "strong_buy" in str(r):
                    bullish_score += 1
                elif "卖出" in text or "看跌" in text or "回避" in text or "strong_sell" in str(r):
                    bullish_score -= 1
                elif "持有" in text or "中性" in text:
                    pass  # 中性不增减
                # 基于信号字段
                signal = r.get("signal", "")
                if signal == "strong_buy":
                    bullish_score += 2
                elif signal == "buy":
                    bullish_score += 1
                elif signal == "strong_sell":
                    bullish_score -= 2
                elif signal == "sell":
                    bullish_score -= 1
        if bullish_score > 1:
            return "买入"
        elif bullish_score < -1:
            return "卖出"
        return "持有"

    def _decide_position(self, direction: str, confidence: int, reports: dict) -> str:
        """动态计算仓位"""
        if direction == "卖出":
            return "空仓或减仓至10%以下"

        # 基于置信度确定仓位档位
        tier_level = confidence - 5  # confidence 0-10, 映射到 -5 ~ 5
        for threshold, position in self.POSITION_TIERS:
            if tier_level >= threshold:
                return position

        return "10%-20%试探仓"

    def _calc_stop_loss(self, direction: str, volatility: float) -> str:
        """动态计算止损位"""
        if direction == "卖出":
            return "-3%"  # 卖出时止损较紧

        for threshold, stop in self.STOP_LOSS_TIERS:
            if volatility <= threshold:
                return stop
        return "-8%"  # 默认

    def _calc_target(self, confidence: int, volatility: float, direction: str) -> str:
        """动态计算目标价"""
        if direction == "卖出":
            return "-5%至-10%（止盈离场）"

        # 风险回报比: 目标至少是止损的 2 倍
        base_vol = max(volatility, 0.2)
        target_multiplier = 1.5 + (confidence / 10)  # 1.5x ~ 2.5x
        target_pct = base_vol * target_multiplier
        pct_str = f"+{target_pct * 100:.0f}%"
        return pct_str

    def _generate_reason(self, direction: str, position: str, reports: dict) -> str:
        """生成决策理由摘要"""
        parts = [f"综合多维度分析，建议{direction}"]
        if direction != "持有":
            parts.append(f"，仓位{position}")

        # 统计各Agent意见
        buy_count = 0
        sell_count = 0
        for r in reports.values():
            if isinstance(r, dict):
                text = str(r.get("analysis", "")).lower()
                if any(kw in text for kw in ("买入", "看涨")):
                    buy_count += 1
                elif any(kw in text for kw in ("卖出", "看跌")):
                    sell_count += 1

        if buy_count > 0:
            parts.append(f"（{buy_count}位分析师看多，{sell_count}位看空）")
        return " ".join(parts)

    def _calc_confidence(self, reports: dict) -> int:
        """动态计算置信度"""
        scores = []
        for r in reports.values():
            if isinstance(r, dict):
                # 从技术分析信号获取
                signal = r.get("signal", "")
                if signal == "strong_buy":
                    scores.append(9)
                elif signal == "buy":
                    scores.append(7)
                elif signal == "strong_sell":
                    scores.append(8)  # 卖出信号置信度
                elif signal == "sell":
                    scores.append(6)
                elif signal == "neutral":
                    scores.append(4)
                # 从研究员辩论获取
                debate_log = r.get("debate_log")
                if debate_log and len(debate_log) >= 2:
                    scores.append(6)
        if not scores:
            return 5  # 默认
        return min(max(sum(scores) // len(scores), 1), 10)

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
