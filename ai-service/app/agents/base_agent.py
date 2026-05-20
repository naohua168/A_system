"""多智能体基类 - 所有 Agent 的抽象基类"""
import json
import httpx
from abc import ABC, abstractmethod
from loguru import logger
from typing import Optional

from app.config import settings
from app.models.deepseek_client import AIClient
from app.models.simulation import get_mock_data, select_dialog_template


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
        """模拟回复（降级方案）— 使用统一模板库"""
        last_msg = messages[-1]["content"] if messages else ""
        template = select_dialog_template(last_msg)
        data = get_mock_data(last_msg)
        try:
            return template.format(**data)
        except KeyError:
            return select_dialog_template("").format(query=last_msg, **get_mock_data(last_msg))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} role={self.role}>"
