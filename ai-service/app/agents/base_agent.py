"""多智能体基类 - 所有 Agent 的抽象基类"""
import json
import httpx
from abc import ABC, abstractmethod
from loguru import logger
from typing import Optional

from app.config import settings
from app.models.deepseek_client import AIClient, MOCK_TEMPLATES


class BaseAgent(ABC):
    """Agent 抽象基类"""

    def __init__(self, name: str, role: str, system_prompt: str = "",
                 model_client: Optional[AIClient] = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model_client = model_client or AIClient()

    @abstractmethod
    async def analyze(self, context: dict) -> dict:
        """分析并返回结果"""
        raise NotImplementedError

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """调用 AI 模型进行对话"""
        if self.system_prompt:
            messages_with_system = [{"role": "system", "content": self.system_prompt}] + messages
            return await self.model_client.chat(messages_with_system, temperature, max_tokens)
        return await self.model_client.chat(messages, temperature, max_tokens)

    async def _fetch_backend_data(self, endpoint: str, params: dict = None) -> dict:
        """调用后端 API 获取数据，超时5秒，失败返回空字典"""
        url = f"{settings.backend_api_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"[{self.name}] 后端 API 调用失败 {endpoint}: {e}")
            return {}

    def _mock_reply(self, messages: list[dict]) -> str:
        """模拟回复（降级方案）"""
        last_msg = messages[-1]["content"] if messages else ""
        query = last_msg.lower()

        mock_data = {
            "ma5": "5.28", "ma10": "5.15", "ma20": "4.98",
            "dif": "0.15", "dea": "0.08",
            "k": "72", "d": "65", "j": "86",
            "resistance": "5.60元", "support": "4.80元",
            "mid": "5.10",
            "central_low": "12.50", "central_high": "13.80",
            "target1": "14.50元", "target2": "15.80元",
            "month_ret": 3.5, "quarter_ret": 8.2, "half_ret": -2.1,
            "max_drawdown": 12.5,
            "top_holdings": "茅台、宁德时代、招商银行",
            "industry": "消费+新能源+金融",
            "conc_level": "较高",
            "volatility": 18.5, "sharpe": 1.2,
            "sh_index": "3,158.26", "sh_change": 0.68,
            "sz_index": "10,542.35", "sz_change": 1.24,
            "cy_index": "2,285.45", "cy_change": 1.86,
            "volume": "8,562", "volume_compare": True, "volume_diff": "15.3",
            "foreign_inflow": "42.5",
            "hot_sector": "AI算力、半导体",
            "query": query,
        }

        if "涨" in query or "看多" in query or "买入" in query:
            template = MOCK_TEMPLATES.get("trend_bullish", MOCK_TEMPLATES["general_advice"])
        elif "跌" in query or "看空" in query or "卖出" in query:
            template = MOCK_TEMPLATES.get("trend_bearish", MOCK_TEMPLATES["general_advice"])
        else:
            template = MOCK_TEMPLATES.get("fund_analysis" if "基金" in query else "general_advice", MOCK_TEMPLATES["general_advice"])

        try:
            return template.format(**mock_data)
        except KeyError:
            return MOCK_TEMPLATES["general_advice"].format(query=query)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} role={self.role}>"
