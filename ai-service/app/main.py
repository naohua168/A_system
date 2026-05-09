"""AI 对话服务 - FastAPI 入口"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api.dialogue import router as dialogue_router
from app.models.deepseek_client import client

app = FastAPI(
    title="AI 对话服务",
    description="基金股票智能分析系统 - AI 对话微服务",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(dialogue_router)


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "ai_mode": client.status["mode"]}


if __name__ == "__main__":
    logger.info(f"🚀 AI 服务启动: {settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)
