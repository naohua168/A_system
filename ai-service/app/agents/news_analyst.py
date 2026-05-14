"""新闻分析师 - 分析新闻情绪与事件影响"""
from loguru import logger

from app.agents.base_agent import BaseAgent


NEWS_SYSTEM_PROMPT = """你是一位新闻情绪分析师，擅长分析新闻事件对股价的影响。
请基于新闻数据进行分析：
- 新闻标题与内容摘要
- 新闻来源与发布时间
- 相关公司/行业
- 新闻情感倾向（正面/负面/中性）

分析维度：
1. 新闻情绪：整体情感倾向
2. 事件影响：对股价的潜在影响程度
3. 时效性：新闻的及时性
4. 操作建议：基于新闻面的操作提示

请给出客观的新闻情绪分析结论。"""


class NewsAnalyst(BaseAgent):
    """新闻分析师"""

    def __init__(self, model_client=None):
        super().__init__(
            name="news_analyst",
            role="新闻分析师",
            system_prompt=NEWS_SYSTEM_PROMPT,
        )

    async def analyze(self, context: dict) -> dict:
        stock_code = context.get("stock_code", "")
        logger.info(f"[新闻分析师] 开始分析 {stock_code}")

        # 调用后端新闻 API
        news_data = await self._fetch_backend_data(f"/api/news/{stock_code}")

        if not news_data:
            news_data = self._mock_news_data(stock_code)

        messages = [
            {"role": "user", "content": (
                f"请分析股票 {stock_code} 的相关新闻：\n{self._format_news(news_data)}"
            )}
        ]

        try:
            analysis_text = await self.chat(messages)
        except Exception as e:
            logger.error(f"[新闻分析师] AI 分析失败: {e}")
            analysis_text = self._mock_analysis(news_data)

        result = {
            "agent": self.name,
            "role": self.role,
            "stock_code": stock_code,
            "data": news_data,
            "analysis": analysis_text,
            "sentiment_score": self._calculate_sentiment(news_data),
        }
        return result

    def _format_news(self, data: dict) -> str:
        if not data or "articles" not in data:
            return "暂无新闻数据"
        articles = data.get("articles", [])
        if not articles:
            return "暂无新闻数据"
        lines = []
        for i, art in enumerate(articles[:5], 1):
            lines.append(
                f"新闻{i}: 【{art.get('sentiment', '中性')}】{art.get('title', 'N/A')}\n"
                f"    来源: {art.get('source', 'N/A')}  时间: {art.get('time', 'N/A')}\n"
                f"    摘要: {art.get('summary', 'N/A')}"
            )
        return "\n".join(lines)

    def _mock_news_data(self, code: str) -> dict:
        return {
            "stock_code": code,
            "articles": [
                {
                    "title": "行业利好政策出台，XXX板块迎发展机遇",
                    "source": "证券时报",
                    "time": "2026-05-13 09:30",
                    "sentiment": "正面",
                    "summary": "相关部门出台利好政策，支持行业高质量发展，龙头企业有望受益。",
                },
                {
                    "title": "公司发布新品，市场反响积极",
                    "source": "e公司",
                    "time": "2026-05-12 15:00",
                    "sentiment": "正面",
                    "summary": "公司发布新一代产品，技术领先，获得多家机构看好。",
                },
                {
                    "title": "北向资金持续增持，持仓比例创新高",
                    "source": "东方财富",
                    "time": "2026-05-12 18:20",
                    "sentiment": "正面",
                    "summary": "北向资金连续3个交易日净买入，外资看好公司长期发展。",
                },
            ],
        }

    def _calculate_sentiment(self, data: dict) -> float:
        """计算新闻情绪得分 -1.0 ~ 1.0"""
        articles = data.get("articles", [])
        if not articles:
            return 0.0
        scores = {"正面": 1.0, "负面": -1.0, "中性": 0.0}
        total = sum(scores.get(a.get("sentiment", "中性"), 0.0) for a in articles)
        return round(total / len(articles), 2)

    def _mock_analysis(self, data: dict) -> str:
        score = self._calculate_sentiment(data)
        sentiment_text = "积极" if score > 0.3 else "消极" if score < -0.3 else "中性"
        articles = data.get("articles", [])

        return (
            f"**新闻情绪分析**\n\n"
            f"1. **整体情绪**：近期相关新闻情感偏向{sentiment_text}（得分{score}）。\n"
            f"2. **重要事件**：\n"
            + "\n".join(
                f"   - {a.get('title', 'N/A')}（{a.get('sentiment', '中性')}）"
                for a in articles
            ) + "\n"
            f"3. **影响评估**：" + (
                "多项利好叠加，对股价有正面推动作用。" if score > 0.3 else
                "负面消息较多，需警惕风险。" if score < -0.3 else
                "消息面较为平静，无明显催化因素。"
            ) + "\n"
            f"4. **关注重点**：后续关注政策落地进度和公司基本面变化。\n\n"
            f"⚠️ 新闻情绪仅供参考，需结合其他维度综合判断。"
        )
