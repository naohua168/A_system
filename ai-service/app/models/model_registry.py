"""统一模型目录 — 支持多模型接入（SiliconFlow + DeepSeek 双后端）"""
from typing import Optional
from loguru import logger

from app.models.deepseek_client import AIClient
from app.config import settings


class ModelRegistry:
    """AI 模型目录，支持多后端模型接入和自动故障转移

    优先级: SiliconFlow → DeepSeek → mock（均自动检测）
    """

    _models = {}

    @classmethod
    def register_model(cls, name: str, client: AIClient):
        cls._models[name] = client
        logger.info(f"✅ 注册模型: {name}")

    @classmethod
    def get_client(cls, model_type: str = "siliconflow", api_key: Optional[str] = None) -> AIClient:
        """获取模型客户端（自动检测可用后端）"""
        cache_key = f"{model_type}:{api_key or 'default'}"

        if cache_key in cls._models:
            return cls._models[cache_key]

        client = AIClient()
        # 如果指定了 api_key，优先使用
        if api_key:
            client.api_key = api_key
            client.mock_mode = False
            client.backend = model_type

        # 根据 model_type 设置正确的 API URL 和模型名
        if model_type == "siliconflow" and settings.siliconflow_api_key:
            client.backend = "siliconflow"
            client.api_key = settings.siliconflow_api_key
            client.api_url = settings.siliconflow_api_url
            client.model = settings.siliconflow_model
            client.mock_mode = False
        elif model_type == "deepseek" and settings.deepseek_api_key:
            client.backend = "deepseek"
            client.api_key = settings.deepseek_api_key
            client.api_url = settings.deepseek_api_url
            client.model = settings.deepseek_model
            client.mock_mode = False

        cls._models[cache_key] = client
        return client

    @classmethod
    def list_models(cls) -> list:
        """列出所有可用模型"""
        models = [
            "siliconflow",
            "deepseek-chat",
            "deepseek-reasoner",
        ]
        # 如果配置了 SiliconFlow，列出其推荐模型
        if settings.siliconflow_api_key:
            models.extend([
                "Qwen/Qwen2.5-72B-Instruct",
                "Qwen/Qwen2.5-32B-Instruct",
                "deepseek-ai/DeepSeek-V3",
                "deepseek-ai/DeepSeek-R1",
                "THUDM/glm-4-9b-chat",
            ])
        return models

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
    async def auto_fallback(cls, primary: str = "siliconflow",
                            fallbacks: list[str] | None = None,
                            messages: list | None = None) -> str:
        """自动故障转移：主模型失败后依次尝试备用模型"""
        if messages is None:
            messages = []
        if fallbacks is None:
            fallbacks = ["deepseek", "mock"]
        errors = []
        models_to_try = [primary] + fallbacks

        for model_name in models_to_try:
            try:
                client = cls.get_client(model_name)
                if client.mock_mode:
                    return client.chat(messages)
                return await client.chat(messages)
            except Exception as e:
                errors.append(f"[{model_name}] {e}")
                logger.warning(f"模型 {model_name} 失败: {e}")
                continue

        logger.error(f"所有模型失败: {errors}")
        return "抱歉，当前所有AI模型均不可用，请稍后重试。"


# 注册默认模型 — AIClient 会自动检测 SiliconFlow/DeepSeek/mock
_default_client = AIClient()
ModelRegistry.register_model("siliconflow", _default_client)
if settings.deepseek_api_key:
    _deepseek_client = AIClient()
    ModelRegistry.register_model("deepseek-chat", _deepseek_client)
