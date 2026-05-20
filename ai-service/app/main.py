"""AI 对话服务 - FastAPI 入口"""
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api.dialogue import router as dialogue_router
from app.models.deepseek_client import client as deepseek_client
from app.models.siliconflow_client import siliconflow_client, init_siliconflow_client
from app.services.memory_service import redis_client
from app.fusion import fusion_engine

# ── 全局模型客户端映射（供 health/status 查询） ──
MODEL_CLIENTS = {
    "deepseek": deepseek_client,
    # siliconflow 在 startup 中按需初始化
}

app = FastAPI(
    title="AI 对话服务",
    description="基金股票智能分析系统 - AI 对话微服务",
    version="2.0.0",
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

# ── FusionEngine 定时权重学习配置 ──
WEIGHT_LEARN_INTERVAL_SECONDS = 3600  # 默认每小时学习一次


async def _weight_learn_task():
    """后台任务：周期性调用 FusionEngine.learn_weights() 自动调整 Agent 权重"""
    while True:
        try:
            await asyncio.sleep(WEIGHT_LEARN_INTERVAL_SECONDS)
            # learn_weights 是同步方法，在线程池中执行以避免阻塞事件循环
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, fusion_engine.learn_weights)
            logger.info("FusionEngine 定时权重学习完成")
        except asyncio.CancelledError:
            logger.info("FusionEngine 定时权重学习任务已取消")
            break
        except Exception as e:
            logger.warning(f"FusionEngine 定时权重学习失败: {e}")


_learn_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    """应用启动时初始化各服务（失败不阻止启动，以降级模式运行）"""
    # 1. Redis 连接
    try:
        await redis_client.connect()
    except Exception as e:
        logger.warning(f"启动时 Redis 连接失败，将使用文件存储降级: {e}")

    # 2. 硅基流动客户端（如配置了 API Key）
    if settings.siliconflow_api_key:
        try:
            init_siliconflow_client(settings.siliconflow_api_key)
            MODEL_CLIENTS["siliconflow"] = siliconflow_client
            logger.info(f"硅基流动客户端已初始化 (模型: {settings.siliconflow_model})")
        except Exception as e:
            logger.warning(f"硅基流动客户端初始化失败（降级）: {e}")
    else:
        logger.info("未配置 SILICONFLOW_API_KEY，硅基流动客户端跳过")

    # 3. 初始化 FusionEngine Redis 连接（复用 memory_service 的 redis_client）
    if redis_client.available:
        try:
            fusion_engine._redis = redis_client.client
            logger.info("FusionEngine Redis 连接已建立")
        except Exception as e:
            logger.warning(f"FusionEngine Redis 连接失败: {e}")
    else:
        logger.info("FusionEngine 未连接 Redis，跳过权重持久化")

    # 4. 启动定时权重学习后台任务
    global _learn_task
    _learn_task = asyncio.create_task(_weight_learn_task())
    logger.info(f"FusionEngine 定时权重学习已启动 (间隔: {WEIGHT_LEARN_INTERVAL_SECONDS}s)")

    # 5. 打印模型状态摘要
    for name, cli in MODEL_CLIENTS.items():
        try:
            info = cli.status if hasattr(cli, "status") else {"unknown": True}
            logger.info(f"  [{name}] {info}")
        except Exception:
            pass


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时清理资源"""
    global _learn_task
    if _learn_task:
        _learn_task.cancel()
        try:
            await _learn_task
        except asyncio.CancelledError:
            pass
        logger.info("FusionEngine 定时权重学习任务已停止")


@app.get("/health")
async def health():
    """健康检查 - 返回各模块状态"""
    statuses = {}
    for name, cli in MODEL_CLIENTS.items():
        try:
            statuses[name] = cli.status if hasattr(cli, "status") else {"available": True}
        except Exception as e:
            statuses[name] = {"error": str(e)}
    
    return {
        "status": "ok",
        "version": "2.0.0",
        "models": statuses,
        "redis": redis_client.available,
    }


if __name__ == "__main__":
    logger.info(f"🚀 AI 服务启动: {settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)
