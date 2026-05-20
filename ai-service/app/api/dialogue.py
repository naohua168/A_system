"""对话 API 路由 — 完整暴露 L5 层所有功能"""
import re
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from loguru import logger

from app.services.dialogue_service import dialogue_service
from app.services.multi_agent_service import multi_agent_service
from app.services.memory_service import memory_service
from app.config import settings
from app.models.deepseek_client import client as deepseek_client
from app.models.model_registry import ModelRegistry
from app.fusion import fusion_engine

router = APIRouter(prefix="/api/ai", tags=["AI Dialogue"])


# ── 请求/响应模型 ──

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
        return v[-20:]


class ChatResponse(BaseModel):
    reply: str


class AnalyzeRequest(BaseModel):
    stock_code: str

    @field_validator("stock_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not re.match(r"^\d{6}$", v.strip()):
            raise ValueError("股票代码格式错误，应为6位数字")
        return v.strip()


class DebateRequest(BaseModel):
    stock_code: str
    rounds: int = 3

    @field_validator("stock_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not re.match(r"^\d{6}$", v.strip()):
            raise ValueError("股票代码格式错误，应为6位数字")
        return v.strip()

    @field_validator("rounds")
    @classmethod
    def validate_rounds(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("辩论轮数应在1-10之间")
        return v


class FuseRequest(BaseModel):
    stock_code: str
    reports: dict | None = None

    @field_validator("stock_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if v and not re.match(r"^\d{6}$", v.strip()):
            raise ValueError("股票代码格式错误，应为6位数字")
        return v.strip()


# ── 鉴权 ──

async def verify_api_key(x_api_key: str = Header("")):
    if settings.ai_api_key and x_api_key != settings.ai_api_key:
        raise HTTPException(status_code=401, detail="无效的 API Key")


# ── 已暴露接口 ──

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest):
    """AI 对话接口（注入实时行情上下文）"""
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
    return deepseek_client.status


# ── 新增接口: POST /api/ai/analyze — 多智能体深度分析 ──

@router.post("/analyze", dependencies=[Depends(verify_api_key)])
async def analyze(req: AnalyzeRequest):
    """多智能体深度分析：7 个 Agent 并行分析 + FusionEngine 加权融合"""
    try:
        result = await multi_agent_service.analyze_stock(req.stock_code)
        return {
            "success": True,
            "stock_code": req.stock_code,
            "fused_decision": result.get("fused_decision", {}),
            "reports": {k: self._summary(v) for k, v in result.get("reports", {}).items()},
        }
    except Exception as e:
        logger.error(f"多智能体分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")

    @staticmethod
    def _summary(report: dict) -> dict:
        """提取关键摘要"""
        return {
            "agent": report.get("agent", report.get("role", "")),
            "status": "ok" if "error" not in report else "failed",
            "signal": report.get("signal", ""),
            "sentiment": report.get("sentiment", ""),
            "sentiment_score": report.get("sentiment_score"),
            "risk_level": report.get("risk_level", ""),
            "direction": report.get("direction", ""),
            "confidence": report.get("confidence"),
        }


# ── 新增接口: POST /api/ai/debate — 研究员辩论 ──

@router.post("/debate", dependencies=[Depends(verify_api_key)])
async def debate(req: DebateRequest):
    """研究员辩论：多轮看涨 vs 看跌辩论"""
    try:
        result = await multi_agent_service.iterative_debate(req.stock_code, req.rounds)
        return {
            "success": True,
            "stock_code": req.stock_code,
            "debate_rounds": result.get("debate_rounds", req.rounds),
            "conclusion": result.get("conclusion", ""),
            "debate_log": result.get("debate_log", []),
        }
    except Exception as e:
        logger.error(f"辩论分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"辩论失败: {e}")


# ── 新增接口: POST /api/ai/chat/stream — SSE 流式对话 ──

@router.post("/chat/stream", dependencies=[Depends(verify_api_key)])
async def chat_stream(req: ChatRequest):
    """SSE 流式对话（打字机效果）"""
    async def event_generator():
        try:
            # 先构建上下文
            context = await dialogue_service._build_context(req.stock_code)
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            if req.history:
                for msg in req.history[-10:]:
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            messages.append({"role": "user", "content": req.message})

            # SSE 流式输出
            from app.models.siliconflow_client import siliconflow_client
            if siliconflow_client and siliconflow_client.api_key:
                async for chunk in siliconflow_client.chat_stream(messages):
                    if chunk:
                        yield f"data: {chunk}\n\n"
            else:
                # 无 SiliconFlow 时回退到非流式
                from app.models.deepseek_client import client
                reply = await client.chat(messages)
                yield f"data: {reply}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── 新增接口: POST /api/ai/fuse — 融合分析 ──

@router.post("/fuse", dependencies=[Depends(verify_api_key)])
async def fuse(req: FuseRequest):
    """融合分析：对已有的多 Agent 报告进行加权投票融合"""
    try:
        if req.reports:
            # 使用用户提供的报告
            result = fusion_engine.fuse(req.reports)
        else:
            # 新进行一次多智能体分析再融合
            multi_result = await multi_agent_service.analyze_stock(req.stock_code)
            result = multi_result.get("fused_decision", {})

        return {
            "success": True,
            "stock_code": req.stock_code,
            "fused_decision": result,
        }
    except Exception as e:
        logger.error(f"融合分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"融合分析失败: {e}")


# ── 新增接口: GET /api/ai/memory/{code} — 历史记忆查询 ──

@router.get("/memory/{code}", dependencies=[Depends(verify_api_key)])
async def get_memory(code: str, n: int = Query(10, ge=1, le=100)):
    """查询指定股票的历史分析记忆"""
    if not re.match(r"^\d{6}$", code):
        raise HTTPException(status_code=400, detail="股票代码格式错误")

    history = await memory_service.load_history(code, n=n)
    reflection = await memory_service.auto_reflect(code)
    return {
        "success": True,
        "stock_code": code,
        "total_records": reflection.get("total_records", len(history)),
        "history": history,
        "reflection": reflection,
        "all_stocks": await memory_service.get_all_stocks(),
    }


# ── 新增接口: GET /api/ai/models — 模型列表 ──

@router.get("/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """列出所有可用的 AI 模型"""
    return {
        "success": True,
        "available_models": ModelRegistry.list_models(),
        "current": {
            "deepseek": {
                "model": deepseek_client.model,
                "mode": deepseek_client.status.get("mode", "unknown"),
            },
            "siliconflow": {
                "model": settings.siliconflow_model,
                "configured": bool(settings.siliconflow_api_key),
            },
        },
    }
