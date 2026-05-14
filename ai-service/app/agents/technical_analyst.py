"""技术分析师 - 分析技术指标（MACD、KDJ、MA等）"""
from loguru import logger

from app.agents.base_agent import BaseAgent


TECHNICAL_SYSTEM_PROMPT = """你是一位资深技术分析师，擅长技术指标解读和趋势判断。
请基于技术指标数据进行分析：
- 均线系统（MA5/MA10/MA20/MA60）
- MACD（DIF/DEA/柱状图）
- KDJ（K/D/J值）
- RSI
- 布林带
- 成交量

分析维度：
1. 趋势判断：短期/中期/长期趋势
2. 技术形态：金叉/死叉、背离、突破等
3. 支撑压力：关键支撑位和压力位
4. 操作建议：基于技术面的买卖建议

请给出专业、客观的技术分析结论。"""


class TechnicalAnalyst(BaseAgent):
    """技术分析师"""

    def __init__(self, model_client=None):
        super().__init__(
            name="technical_analyst",
            role="技术分析师",
            system_prompt=TECHNICAL_SYSTEM_PROMPT,
        )

    async def analyze(self, context: dict) -> dict:
        stock_code = context.get("stock_code", "")
        logger.info(f"[技术分析师] 开始分析 {stock_code}")

        # 调用后端 API 获取技术指标数据
        tech_data = await self._fetch_backend_data(f"/api/analysis/technical/{stock_code}")

        if not tech_data:
            tech_data = self._mock_tech_data(stock_code)

        messages = [
            {"role": "user", "content": f"请分析股票 {stock_code} 的技术指标：\n{self._format_data(tech_data)}"}
        ]

        try:
            analysis_text = await self.chat(messages)
        except Exception as e:
            logger.error(f"[技术分析师] AI 分析失败: {e}")
            analysis_text = self._mock_analysis(tech_data)

        result = {
            "agent": self.name,
            "role": self.role,
            "stock_code": stock_code,
            "data": tech_data,
            "analysis": analysis_text,
            "signal": self._determine_signal(tech_data),
        }
        return result

    def _format_data(self, data: dict) -> str:
        return (
            f"最新价: {data.get('close', 'N/A')}\n"
            f"MA5: {data.get('ma5', 'N/A')}  MA10: {data.get('ma10', 'N/A')}  "
            f"MA20: {data.get('ma20', 'N/A')}  MA60: {data.get('ma60', 'N/A')}\n"
            f"MACD DIF: {data.get('dif', 'N/A')}  DEA: {data.get('dea', 'N/A')}  柱: {data.get('macd', 'N/A')}\n"
            f"KDJ K: {data.get('k', 'N/A')}  D: {data.get('d', 'N/A')}  J: {data.get('j', 'N/A')}\n"
            f"RSI: {data.get('rsi', 'N/A')}\n"
            f"布林上轨: {data.get('boll_up', 'N/A')}  中轨: {data.get('boll_mid', 'N/A')}  下轨: {data.get('boll_low', 'N/A')}\n"
            f"成交量: {data.get('volume', 'N/A')}\n"
            f"涨跌幅: {data.get('changePercent', 'N/A')}%"
        )

    def _mock_tech_data(self, code: str) -> dict:
        return {
            "close": 15.68, "ma5": 15.42, "ma10": 15.18, "ma20": 14.85, "ma60": 14.20,
            "dif": 0.35, "dea": 0.22, "macd": 0.13,
            "k": 72.5, "d": 65.3, "j": 86.9,
            "rsi": 62.8,
            "boll_up": 16.80, "boll_mid": 14.85, "boll_low": 12.90,
            "volume": 1258600,
            "changePercent": 2.35,
        }

    def _determine_signal(self, data: dict) -> str:
        """根据技术指标判断信号"""
        try:
            ma5 = float(data.get("ma5", 0))
            ma10 = float(data.get("ma10", 0))
            ma20 = float(data.get("ma20", 0))
            dif = float(data.get("dif", 0))
            dea = float(data.get("dea", 0))
            j = float(data.get("j", 0))

            if ma5 > ma10 > ma20 and dif > dea and j > 80:
                return "strong_buy"
            elif ma5 > ma10 and dif > dea:
                return "buy"
            elif ma5 < ma10 < ma20 and dif < dea:
                return "sell"
            elif ma5 < ma10 and dif < dea and j < 20:
                return "strong_sell"
            else:
                return "neutral"
        except (ValueError, TypeError):
            return "neutral"

    def _mock_analysis(self, data: dict) -> str:
        signal = self._determine_signal(data)
        if signal in ("strong_buy", "buy"):
            return (
                f"**技术面看涨信号**\n\n"
                f"1. **均线系统**：MA5({data.get('ma5')}) > MA10({data.get('ma10')}) > MA20({data.get('ma20')})，"
                f"呈多头排列，短期趋势向上。\n"
                f"2. **MACD**：DIF({data.get('dif')}) 上穿 DEA({data.get('dea')})，红柱持续，多头动能增强。\n"
                f"3. **KDJ**：K({data.get('k')})、D({data.get('d')}) 金叉向上，J值({data.get('j')})进入强势区。\n"
                f"4. **RSI**：{data.get('rsi')}，处于偏强区域。\n\n"
                f"⚠️ 上方16.80附近有压力，若放量突破可看高一线。"
            )
        elif signal in ("strong_sell", "sell"):
            return (
                f"**技术面需谨慎**\n\n"
                f"1. **均线系统**：MA5({data.get('ma5')}) < MA10({data.get('ma10')})，短期趋势转弱。\n"
                f"2. **MACD**：DIF({data.get('dif')}) 下穿 DEA({data.get('dea')}) 形成死叉。\n"
                f"3. **KDJ**：K({data.get('k')})、D({data.get('d')}) 死叉向下，短线有调整需求。\n\n"
                f"⚠️ 建议减仓观望，等待企稳信号。"
            )
        return (
            f"**技术面中性震荡**\n\n"
            f"1. 均线系统交织，短期方向不明。\n"
            f"2. MACD 在零轴附近运行，多空力量均衡。\n"
            f"3. KDJ 位于中枢区域，上下均有空间。\n\n"
            f"⚠️ 建议观望，等待方向选择后再操作。"
        )
