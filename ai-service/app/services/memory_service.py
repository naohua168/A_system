"""持久化记忆服务 — 优先使用 Redis，不可用时回退到本地文件"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger

from app.config import settings


class RedisClient:
    """Redis 客户端包装器，惰性连接，连接失败时静默降级"""

    def __init__(self):
        self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def connect(self) -> bool:
        if not settings.redis_host:
            return False
        try:
            import redis.asyncio as aioredis

            self._client = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
                socket_connect_timeout=2,
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("记忆服务: Redis 连接成功")
            return True
        except Exception as e:
            logger.warning(f"记忆服务: Redis 不可用 ({e})，回退到文件存储")
            self._client = None
            return False

    async def get(self, key: str) -> Optional[str]:
        if not self.available:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis GET {key} 失败: {e}")
            return None

    async def set(self, key: str, value: str, expire: int = 86400):
        if not self.available:
            return
        try:
            await self._client.set(key, value, ex=expire)
        except Exception as e:
            logger.warning(f"Redis SET {key} 失败: {e}")

    async def keys(self, pattern: str) -> list:
        if not self.available:
            return []
        try:
            return await self._client.keys(pattern)
        except Exception as e:
            logger.warning(f"Redis KEYS {pattern} 失败: {e}")
            return []


redis_client = RedisClient()


class MemoryService:
    """持久化记忆服务 — 优先 Redis，回退本地文件"""

    MEMORY_DIR = Path.home() / ".a_system" / "memory"
    REDIS_PREFIX = "memory:"
    MAX_HISTORY = 100

    def __init__(self):
        self.MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    async def _load_history_redis(self, stock_code: str) -> list:
        """从 Redis 加载历史记录"""
        raw = await redis_client.get(f"{self.REDIS_PREFIX}{stock_code}")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return []

    async def _save_history_redis(self, stock_code: str, history: list):
        """保存历史记录到 Redis"""
        data = json.dumps(history, ensure_ascii=False)
        await redis_client.set(f"{self.REDIS_PREFIX}{stock_code}", data, expire=86400 * 30)

    def _load_history_file(self, stock_code: str) -> list:
        """从文件加载历史记录（同步，降级使用）"""
        fp = self.MEMORY_DIR / f"{stock_code}.json"
        if fp.exists():
            try:
                return json.loads(fp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"读取记忆文件失败: {fp} -> {e}")
        return []

    async def _load_history_file_async(self, stock_code: str) -> list:
        """异步从文件加载历史记录"""
        fp = self.MEMORY_DIR / f"{stock_code}.json"
        if not fp.exists():
            return []
        try:
            content = await asyncio.to_thread(fp.read_text, encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"读取记忆文件失败: {fp} -> {e}")
            return []

    def _save_history_file(self, stock_code: str, history: list):
        """保存历史记录到文件（同步）"""
        fp = self.MEMORY_DIR / f"{stock_code}.json"
        data = json.dumps(history, ensure_ascii=False, indent=2)
        fp.write_text(data, encoding="utf-8")

    async def _load_history(self, stock_code: str) -> list:
        """加载历史记录 — 优先 Redis"""
        if redis_client.available:
            history = await self._load_history_redis(stock_code)
            if history:
                return history
        return await self._load_history_file_async(stock_code)

    async def save_decision(self, stock_code: str, decision: dict) -> str:
        """保存交易决策到持久化存储"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code,
            "decision": decision,
        }

        history = await self._load_history(stock_code)
        history.append(record)

        # 只保留最近 N 条
        if len(history) > self.MAX_HISTORY:
            history = history[-self.MAX_HISTORY:]

        # 优先 Redis
        if redis_client.available:
            await self._save_history_redis(stock_code, history)
            logger.info(f"决策已保存(Redis): {stock_code} ({len(history)}条历史)")
            return f"redis://{stock_code}"

        # 回退文件系统
        data = json.dumps(history, ensure_ascii=False, indent=2)
        fp = self.MEMORY_DIR / f"{stock_code}.json"
        await asyncio.to_thread(fp.write_text, data, encoding="utf-8")
        logger.info(f"决策已保存(File): {stock_code} ({len(history)}条历史)")
        return str(fp)

    async def load_history(self, stock_code: str, n: int = 10) -> list:
        """加载最近 N 条决策历史"""
        history = await self._load_history(stock_code)
        return history[-n:]

    async def auto_reflect(self, stock_code: str) -> dict:
        """自动反思 — 对比当前结论与历史决策"""
        history = await self._load_history(stock_code)
        if len(history) < 2:
            return {"message": "暂无足够的历史数据用于反思", "total_records": len(history)}

        recent = history[-5:]
        directions = []
        for record in recent:
            decision = record.get("decision", {})
            direction = decision.get("direction", decision.get("final_decision", {}).get("action", ""))
            if direction:
                directions.append(direction)

        return {
            "stock_code": stock_code,
            "total_records": len(history),
            "recent_decisions": directions,
            "reflection": "近期操作建议趋于一致" if len(set(directions)) == 1 else "近期建议有分歧,需谨慎",
            "last_updated": recent[-1].get("timestamp", ""),
        }

    async def get_all_stocks(self) -> list:
        """获取所有有记忆的股票列表"""
        stocks = set()

        # 从 Redis 读取
        if redis_client.available:
            keys = await redis_client.keys(f"{self.REDIS_PREFIX}*")
            for key in keys:
                stock = key.replace(self.REDIS_PREFIX, "")
                stocks.add(stock)

        # 从文件读取
        for fp in self.MEMORY_DIR.glob("*.json"):
            stocks.add(fp.stem)

        return sorted(stocks)


memory_service = MemoryService()
