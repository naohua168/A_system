"""AI 对话服务配置"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    deepseek_model: str = "deepseek-chat"

    # Kimi API
    kimi_api_key: str = ""
    kimi_api_url: str = "https://api.moonshot.cn/v1/chat/completions"

    # 后端行情 API
    backend_api_url: str = "http://localhost:8080/api"

    # API 鉴权（可选，不配置时放行所有请求）
    ai_api_key: str = ""

    # Redis 配置（可选，用于记忆持久化）
    redis_host: str = ""
    redis_port: int = 6379
    redis_password: str = ""

    class Config:
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
