"""统一模型目录 — 支持多模型接入"""
from typing import Optional
from loguru import logger

from app.models.deepseek_client import AIClient
from app.config import settings


class ModelRegistry:
    """AI 模型目录，支持多种模型接入和自动故障转移"""

    _models = {}

    @classmethod
    def register_model(cls, name: str, client: AIClient):
        cls._models[name] = client
        logger.info(f"注册模型: {name}")

    @classmethod
    def get_client(cls, model_type: str = "deepseek", api_key: Optional[str] = None) -> AIClient:
        """获取指定类型的模型客户端"""
        cache_key = f"{model_type}:{api_key or 'default'}"

        if cache_key in cls._models:
            return cls._models[cache_key]

        client = AIClient()
        client.model = model_type
        if api_key:
            client.api_key = api_key
            client.mock_mode = False

        cls._models[cache_key] = client
        return client

    @classmethod
    def list_models(cls) -> list:
        """列出所有已注册的模型"""
        return [
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-opus",
            "claude-3-sonnet",
            "qwen-max",
            "qwen-plus",
        ]

    @classmethod
    def health_check(cls) -> dict:
        """检查所有已注册模型的状态"""
        status = {}
        for name, client in cls._models.items():
            try:
                status[name] = client.status
            except Exception as e:
                status[name] = {"error": str(e), "mode": "error"}
        return status

    @classmethod
    async def auto_fallback(cls, primary: str, fallbacks: list[str], messages: list) -> str:
        """自动故障转移：主模型失败后依次尝试备用模型

        修复: 改为 async def 并在 client.chat() 前加 await。
        chat() 是异步方法 (async def)，若不加 await 会返回协程对象而非字符串。
        """
        errors = []
        models_to_try = [primary] + fallbacks

        for model_name in models_to_try:
            try:
                client = cls.get_client(model_name)
                return await client.chat(messages)
            except Exception as e:
                errors.append(f"[{model_name}] {e}")
                logger.warning(f"模型 {model_name} 失败: {e}")
                continue

        logger.error(f"所有模型失败: {errors}")
        return "抱歉，当前所有AI模型均不可用，请稍后重试。"


# 注册默认模型
_default_client = AIClient()
ModelRegistry.register_model("deepseek-chat", _default_client)
