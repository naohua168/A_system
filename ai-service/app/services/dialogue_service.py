"""对话业务服务"""
from app.models.deepseek_client import client


class DialogueService:

    async def chat(self, message: str, stock_code: str = "", history: list[dict] | None = None) -> dict:
        """处理用户对话"""
        # 构建上下文
        context = self._build_context(stock_code)

        # 构建消息列表
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        if history:
            for msg in history[-10:]:  # 保留最近 10 条
                messages.append(msg)
        messages.append({"role": "user", "content": message})

        # 调用 AI
        reply = await client.chat(messages)

        return {"reply": reply}

    def _build_context(self, stock_code: str) -> str:
        """构建股票上下文"""
        if not stock_code:
            return ""
        return f"当前查询的股票/基金代码为 {stock_code}，请针对该标的进行分析。"


dialogue_service = DialogueService()
