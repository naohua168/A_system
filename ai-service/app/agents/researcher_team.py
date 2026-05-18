"""研究员辩论 Agent — 多轮看涨vs看跌辩论"""
import asyncio

from app.agents.base_agent import BaseAgent

BULLISH_PROMPT = "你是一名看涨分析师，请从基本面、技术面、资金面三个角度论证该股票会上涨。"
BEARISH_PROMPT = "你是一名看跌分析师，请从基本面、技术面、资金面三个角度论证该股票会下跌。"


class BullishView(BaseAgent):
    def __init__(self):
        super().__init__("bullish_view", "看涨分析师", BULLISH_PROMPT)

    async def analyze(self, context: dict) -> dict:
        return {"view": "bullish", "reason": "基于技术面多头排列和资金流入"}

    def _mock_reply(self, messages) -> str:
        return (
            "**看涨论据**：\n"
            "1. 均线多头排列，短期趋势向上\n"
            "2. MACD金叉，红柱持续放大\n"
            "3. 北向资金持续流入，主力加仓\n"
            "4. 行业景气度提升，政策利好\n"
            "结论：建议逢低买入，目标涨幅15-20%"
        )


class BearishView(BaseAgent):
    def __init__(self):
        super().__init__("bearish_view", "看跌分析师", BEARISH_PROMPT)

    async def analyze(self, context: dict) -> dict:
        return {"view": "bearish", "reason": "基于技术面顶背离和资金流出"}

    def _mock_reply(self, messages) -> str:
        return (
            "**看跌论据**：\n"
            "1. 股价已到前期压力位，量能不足\n"
            "2. RSI进入超买区，回调风险加大\n"
            "3. 主力资金净流出，散户接盘\n"
            "4. 行业估值偏高，有回调需求\n"
            "结论：建议减仓观望，等待回调10-15%"
        )


class ResearcherTeam(BaseAgent):
    """研究员团队 — 组织多轮辩论"""

    def __init__(self):
        super().__init__("researcher_team", "研究员团队",
                         "你负责组织看涨和看跌分析师进行多轮辩论，最终给出综合投资建议。")
        self.bullish = BullishView()
        self.bearish = BearishView()

    async def analyze(self, context: dict) -> dict:
        rounds = context.get("debate_rounds", 3)
        stock_code = context.get("stock_code", "")

        debate_log = []
        for i in range(rounds):
            # 修复: 并行发起看涨和看跌分析，每轮辩论时间减半
            bullish_task = self.bullish.chat([
                {"role": "user", "content": f"第{i+1}轮辩论，为{stock_code}做看涨分析"}
            ])
            bearish_task = self.bearish.chat([
                {"role": "user", "content": f"第{i+1}轮辩论，回应看涨观点，做看跌分析"}
            ])
            results = await asyncio.gather(bullish_task, bearish_task, return_exceptions=True)
            bullish_arg = self._format_debate_result(results[0], "bullish")
            bearish_arg = self._format_debate_result(results[1], "bearish")
            debate_log.append({"round": i + 1, "bullish": bullish_arg, "bearish": bearish_arg})

        conclusion = await self._synthesize(debate_log, stock_code)
        return {"debate_rounds": rounds, "debate_log": debate_log, "conclusion": conclusion}

    async def _synthesize(self, debate_log: list, stock_code: str) -> str:
        """修复: 基于真实辩论内容生成结论，而非返回硬编码字符串"""
        if not debate_log:
            return f"**{stock_code}**: 辩论未产生有效内容。"

        # 提取最后一轮辩论的关键论点
        last_round = debate_log[-1]
        bullish_short = last_round.get("bullish", "")[:200]
        bearish_short = last_round.get("bearish", "")[:200]

        return (
            f"**{stock_code} 辩论结论**（{len(debate_log)}轮）\n\n"
            f"看涨要点: {bullish_short}\n\n"
            f"看跌要点: {bearish_short}\n\n"
            "**综合建议**：请结合技术面和基本面综合判断。"
        )

    @staticmethod
    def _format_debate_result(result, role: str) -> str:
        """格式化辩论结果，处理异常返回"""
        if isinstance(result, BaseException):
            logger.warning(f"{role} 辩论发生异常: {result}")
            return f"{role}论点获取失败" if role == "bullish" else f"{role}论点获取失败"
        if isinstance(result, str):
            return result
        return str(result) if result else f"{role}未提供论点"

    def _mock_reply(self, messages) -> str:
        return "模拟辩论完成，综合建议：谨慎看多，设好止损位。"
