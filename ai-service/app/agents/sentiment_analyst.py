"""情绪分析师 - 分析市场情绪、题材热点、资金流向"""
from loguru import logger

from app.agents.base_agent import BaseAgent


SENTIMENT_SYSTEM_PROMPT = """你是一位市场情绪分析师，专注于市场情绪和资金流向分析。
请基于以下数据分析市场情绪：
- 题材热点（近期热门概念、板块轮动）
- 资金流向（主力资金、北向资金）
- 龙虎榜数据（游资动向）
- 情绪指标（涨停家数、连板高度、炸板率）

分析维度：
1. 市场情绪：整体情绪（恐慌/平稳/亢奋）
2. 热点持续性：当前热点板块的延续性
3. 资金态度：主力资金和北向资金动向
4. 操作建议：基于情绪面的策略建议

请给出客观的情绪分析结论。"""


class SentimentAnalyst(BaseAgent):
    """情绪分析师"""

    def __init__(self, model_client=None):
        super().__init__(
            name="sentiment_analyst",
            role="情绪分析师",
            system_prompt=SENTIMENT_SYSTEM_PROMPT,
        )

    async def analyze(self, context: dict) -> dict:
        stock_code = context.get("stock_code", "")
        logger.info(f"[情绪分析师] 开始分析 {stock_code}")

        # 修复: 并行发起3个后端调用，总耗时降至最慢的一个; 同时修复双 /api/ 路径
        import asyncio
        industry_task = self._fetch_backend_data(f"/signal/industry")
        dragon_tiger_task = self._fetch_backend_data(f"/signal/dragon-tiger/{stock_code}")
        northbound_task = self._fetch_backend_data(f"/signal/northbound")
        industry_data, dragon_tiger, northbound = await asyncio.gather(
            industry_task, dragon_tiger_task, northbound_task
        )

        if not any([industry_data, dragon_tiger, northbound]):
            industry_data = self._mock_industry_data()
            dragon_tiger = self._mock_dragon_tiger_data()
            northbound = self._mock_northbound_data()

        messages = [
            {"role": "user", "content": (
                f"请分析股票 {stock_code} 的市场情绪：\n\n"
                f"题材板块数据：\n{self._format_industry(industry_data)}\n\n"
                f"龙虎榜数据：\n{self._format_dragon_tiger(dragon_tiger)}\n\n"
                f"北向资金数据：\n{self._format_northbound(northbound)}"
            )}
        ]

        try:
            analysis_text = await self.chat(messages)
        except Exception as e:
            logger.error(f"[情绪分析师] AI 分析失败: {e}")
            analysis_text = self._mock_analysis(industry_data)

        result = {
            "agent": self.name,
            "role": self.role,
            "stock_code": stock_code,
            "data": {
                "industry": industry_data,
                "dragon_tiger": dragon_tiger,
                "northbound": northbound,
            },
            "analysis": analysis_text,
            "sentiment": self._determine_sentiment(industry_data),
        }
        return result

    def _format_industry(self, data: dict) -> str:
        if not data:
            return "暂无数据"
        return (
            f"热门板块: {data.get('hot_industry', 'N/A')}\n"
            f"涨幅: {data.get('change_percent', 'N/A')}%\n"
            f"涨停家数: {data.get('limit_up_count', 'N/A')}"
        )

    def _format_dragon_tiger(self, data: dict) -> str:
        if not data:
            return "暂无数据"
        return (
            f"买入额: {data.get('buy_amount', 'N/A')}\n"
            f"卖出额: {data.get('sell_amount', 'N/A')}\n"
            f"净额: {data.get('net_amount', 'N/A')}\n"
            f"主力席位: {data.get('main_seats', 'N/A')}"
        )

    def _format_northbound(self, data: dict) -> str:
        if not data:
            return "暂无数据"
        return (
            f"沪股通净流入: {data.get('sh_net_inflow', 'N/A')}亿\n"
            f"深股通净流入: {data.get('sz_net_inflow', 'N/A')}亿\n"
            f"合计净流入: {data.get('total_net_inflow', 'N/A')}亿"
        )

    def _mock_industry_data(self) -> dict:
        return {
            "hot_industry": "AI算力、半导体、机器人",
            "change_percent": 3.25,
            "limit_up_count": 15,
        }

    def _mock_dragon_tiger_data(self) -> dict:
        return {
            "buy_amount": "1.25亿",
            "sell_amount": "0.86亿",
            "net_amount": "+0.39亿",
            "main_seats": "中信证券上海分公司、华泰证券总部",
        }

    def _mock_northbound_data(self) -> dict:
        return {
            "sh_net_inflow": 18.5,
            "sz_net_inflow": 23.7,
            "total_net_inflow": 42.2,
        }

    def _determine_sentiment(self, data: dict) -> str:
        try:
            change = float(data.get("change_percent", 0))
            limit_up = int(data.get("limit_up_count", 0))
            if change > 2 and limit_up > 10:
                return "亢奋"
            elif change > 0:
                return "平稳偏多"
            elif change > -2:
                return "平稳偏空"
            return "恐慌"
        except (ValueError, TypeError):
            return "平稳"

    def _mock_analysis(self, data: dict) -> str:
        sentiment = self._determine_sentiment(data)
        industry = data.get("hot_industry", "综合")
        return (
            f"**市场情绪分析**\n\n"
            f"1. **市场情绪**：当前情绪{sentiment}。\n"
            f"2. **热点方向**：{industry}板块表现活跃，资金关注度较高。\n"
            f"3. **资金态度**：北向资金净流入{self._mock_northbound_data().get('total_net_inflow')}亿，"
            f"外资态度偏积极。龙虎榜数据显示主力资金净买入，游资参与度较高。\n"
            f"4. **持续性判断**：热点板块具有一定的持续性，但仍需关注政策面和资金面变化。\n\n"
            f"⚠️ 情绪指标变化较快，需结合基本面和技术面综合判断。"
        )
