"""对话 API 路由"""
import re
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, field_validator
from loguru import logger

from app.services.dialogue_service import dialogue_service
from app.config import settings

router = APIRouter(prefix="/api/ai", tags=["AI Dialogue"])


class ChatRequest(BaseModel):
    message: str
    stock_code: str = ""
    history: list[dict] | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("消息不能为空")
        if len(v) > 2000:
            raise ValueError("消息长度不能超过2000字")
        return v.strip()

    @field_validator("stock_code")
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        if v and not re.match(r"^\d{6}$", v.strip()):
            raise ValueError("股票代码格式错误，应为6位数字")
        return v.strip() if v else ""

    @field_validator("history")
    @classmethod
    def validate_history(cls, v: list[dict] | None) -> list[dict] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("history 必须为列表")
        if len(v) > 50:
            raise ValueError("历史消息不能超过50条")
        for i, msg in enumerate(v):
            if not isinstance(msg, dict):
                raise ValueError(f"history[{i}] 必须为字典")
            if "role" not in msg or "content" not in msg:
                raise ValueError(f"history[{i}] 缺少 role 或 content 字段")
        return v[-20:]  # 限制最多20条


class ChatResponse(BaseModel):
    reply: str


async def verify_api_key(x_api_key: str = Header("")):
    """API 请求鉴权（可选）。仅在 ai_api_key 配置时才校验。"""
    if settings.ai_api_key and x_api_key != settings.ai_api_key:
        raise HTTPException(status_code=401, detail="无效的 API Key")


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest):
    """AI 对话接口"""
    try:
        result = await dialogue_service.chat(req.message, req.stock_code, req.history)
        return ChatResponse(reply=result["reply"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话处理异常: {e}")
        return ChatResponse(reply="抱歉，AI 服务暂时不可用，请稍后重试。")


@router.get("/status")
async def status():
    """AI 服务状态"""
    from app.models.deepseek_client import client
    return client.status
