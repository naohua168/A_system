"""对话 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.dialogue_service import dialogue_service

router = APIRouter(prefix="/api/ai", tags=["AI Dialogue"])


class ChatRequest(BaseModel):
    message: str
    stock_code: str = ""
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """AI 对话接口"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    result = await dialogue_service.chat(req.message, req.stock_code, req.history)
    return ChatResponse(reply=result["reply"])


@router.get("/status")
async def status():
    """AI 服务状态"""
    from app.models.deepseek_client import client
    return client.status
