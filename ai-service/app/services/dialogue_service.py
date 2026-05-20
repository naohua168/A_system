"""对话业务服务 — 接入后端实时数据"""
import asyncio
import re
import httpx
from loguru import logger

from app.config import settings
from app.models.deepseek_client import client as ai_client


class DialogueService:

    async def chat(self, message: str, stock_code: str = "", history: list[dict] | None = None) -> dict:
        """处理用户对话，注入实时股票数据到上下文

        Args:
            message: 用户消息（已被上层校验非空且≤2000字）
            stock_code: 股票代码（可选，空字符串时不构建上下文）
            history: 历史消息记录（已被上层校验格式并限制≤20条）
        Returns:
            {"reply": "AI回复内容"}
        """
        try:
            # 构建含实时数据的上下文
            context = await self._build_context(stock_code)

            # 构建消息列表
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            if history:
                for msg in history[-10:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": message})

            # 调用 AI
            reply = await ai_client.chat(messages)
            return {"reply": reply}
        except Exception as e:
            logger.error(f"对话处理失败: {e}")
            return {"reply": "抱歉，AI 服务暂时不可用，请稍后重试。"}

    async def _build_context(self, stock_code: str) -> str:
        """构建含实时数据的股票上下文 — 调用后端API获取真实数据"""
        code = stock_code.strip()
        if not code or not re.match(r"^\d{6}$", code):
            return ""

        base_url = settings.backend_api_url.rstrip("/")

        async with httpx.AsyncClient(timeout=5.0) as client:

            async def _fetch(path: str) -> dict:
                try:
                    resp = await client.get(f"{base_url}{path}")
                    return resp.json() if resp.status_code == 200 else {}
                except Exception as e:
                    logger.warning(f"获取 {path} 失败: {e}")
                    return {}

            stock_task = _fetch(f"/market/{code}")
            analysis_task = _fetch(f"/analysis/{code}")
            signal_task = _fetch(f"/signal/northbound/latest")
            results = await asyncio.gather(
                stock_task, analysis_task, signal_task,
                return_exceptions=True,
            )
            # 处理可能的异常返回值
            stock_data = results[0] if not isinstance(results[0], BaseException) else {}
            analysis_data = results[1] if not isinstance(results[1], BaseException) else {}
            signal_data = results[2] if not isinstance(results[2], BaseException) else {}

        # 构建上下文
        parts = [f"当前查询标的: {code}"]

        if stock_data:
            name = stock_data.get("stockName", stock_data.get("name", ""))
            price = stock_data.get("price", stock_data.get("closePrice", "N/A"))
            change = stock_data.get("changePercent", stock_data.get("changePct", "N/A"))
            pe = stock_data.get("pe", "N/A")
            pb = stock_data.get("pb", "N/A")
            mcap = stock_data.get("totalMarketCap", stock_data.get("mcapYi", "N/A"))
            parts.append(
                f"实时行情: {name} 股价{price} 涨跌幅{change}% "
                f"PE={pe} PB={pb} 市值={mcap}亿"
            )

        if analysis_data:
            ma5 = analysis_data.get("ma5", "N/A")
            ma20 = analysis_data.get("ma20", "N/A")
            macd = analysis_data.get("macd", {}).get("dif", "N/A")
            rsi = analysis_data.get("rsi", "N/A")
            parts.append(
                f"技术指标: MA5={ma5} MA20={ma20} MACD_DIF={macd} RSI={rsi}"
            )

        if signal_data:
            hot = signal_data.get("hotCount", 0)
            northbound = signal_data.get("northboundNetInflow", "N/A")
            if hot or northbound != "N/A":
                parts.append(
                    f"市场信号: 题材热度{hot}只 北向资金净流入{northbound}亿"
                )

        parts.append("请基于以上真实数据，给出专业的投资分析建议。")

        return "\n".join(parts)


dialogue_service = DialogueService()
