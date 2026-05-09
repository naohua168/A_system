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

    class Config:
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
