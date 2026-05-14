"""持久化记忆服务 — 决策日志存储和反思"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from loguru import logger


class MemoryService:
    """持久化记忆服务"""

    MEMORY_DIR = Path.home() / ".a_system" / "memory"

    def __init__(self):
        self.MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    async def save_decision(self, stock_code: str, decision: dict) -> str:
        """保存交易决策到持久化存储"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code,
            "decision": decision,
        }

        fp = self.MEMORY_DIR / f"{stock_code}.json"
        history = self._load_history(stock_code)
        history.append(record)

        # 只保留最近100条
        if len(history) > 100:
            history = history[-100:]

        fp.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"决策已保存: {stock_code} ({len(history)}条历史)")
        return str(fp)

    async def load_history(self, stock_code: str, n: int = 10) -> list:
        """加载最近N条决策历史"""
        history = self._load_history(stock_code)
        return history[-n:]

    async def auto_reflect(self, stock_code: str) -> dict:
        """自动反思 — 对比当前结论与历史决策"""
        history = self._load_history(stock_code)
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

    def _load_history(self, stock_code: str) -> list:
        """从文件加载历史记录"""
        fp = self.MEMORY_DIR / f"{stock_code}.json"
        if fp.exists():
            try:
                return json.loads(fp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"读取记忆文件失败: {fp} -> {e}")
                return []
        return []

    async def get_all_stocks(self) -> list:
        """获取所有有记忆的股票列表"""
        stocks = []
        for fp in self.MEMORY_DIR.glob("*.json"):
            stocks.append(fp.stem)
        return sorted(stocks)


memory_service = MemoryService()
