"""AI 对话服务配置"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000

    # 日志级别（DEBUG / INFO / WARNING / ERROR）
    log_level: str = "INFO"

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    deepseek_model: str = "deepseek-chat"

    # ── 硅基流动 SiliconFlow API（OpenAI 兼容协议） ──
    siliconflow_api_key: str = ""
    siliconflow_api_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    # 推荐模型: Qwen/Qwen2.5-32B-Instruct, Pro/deepseek-ai/DeepSeek-V3,
    #            deepseek-ai/DeepSeek-R1, Qwen/Qwen2.5-72B-Instruct
    siliconflow_model: str = "Qwen/Qwen2.5-32B-Instruct"

    # 后端行情 API（注意：L4 后端实际端口为 8082）
    backend_api_url: str = "http://localhost:8082/api"

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
