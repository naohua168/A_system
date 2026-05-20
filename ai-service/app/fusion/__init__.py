"""多智能体融合引擎 — 加权投票聚合 + 权重自动学习"""
import json
from loguru import logger
from typing import Optional


class FusionEngine:
    """多智能体融合引擎

    核心功能：
    - 加权投票聚合多个 Agent 的分析结果
    - 动态更新 Agent 权重，自动归一化
    - 基于历史准确率的权重自动学习 (Redis 持久化)

    权重持久化键: fusion:weights (Redis Hash)
    准确率追踪键: fusion:accuracy:{agent_name} (Redis List, 最近100条)
    """

    DEFAULT_WEIGHTS = {
        "technical_analyst": 0.25,
        "fundamentals_analyst": 0.20,
        "sentiment_analyst": 0.15,
        "news_analyst": 0.15,
        "researcher_team": 0.15,
        "trader_agent": 0.05,
        "risk_manager": 0.05,
    }
    ACCURACY_KEY_PREFIX = "fusion:accuracy:"
    WEIGHT_KEY = "fusion:weights"
    MAX_ACCURACY_RECORDS = 100

    def __init__(self, weights: dict[str, float] | None = None, redis_client=None):
        """初始化融合引擎

        Args:
            weights: 自定义权重（为 None 时使用默认值）
            redis_client: Redis 客户端（为 None 时跳过持久化）
        """
        self._redis = redis_client
        self._weights = weights or dict(self.DEFAULT_WEIGHTS)
        self._normalize()
        # 尝试从 Redis 加载已学习的权重
        self._load_weights()

    # ==================== 权重持久化 ====================

    def _load_weights(self):
        """从 Redis 加载持久化的权重"""
        if not self._redis:
            return
        try:
            stored = self._redis.hgetall(self.WEIGHT_KEY)
            if stored:
                parsed = {k: float(v) for k, v in stored.items() if k in self._weights}
                if parsed:
                    self._weights.update(parsed)
                    self._normalize()
                    logger.info(f"融合引擎: 从 Redis 加载了 {len(parsed)} 个持久化权重")
        except Exception as e:
            logger.warning(f"融合引擎: Redis 加载权重失败 ({e})，使用默认权重")

    def _save_weights(self):
        """将当前权重持久化到 Redis"""
        if not self._redis:
            return
        try:
            mapping = {k: str(round(v, 4)) for k, v in self._weights.items()}
            self._redis.hset(self.WEIGHT_KEY, mapping=mapping)
        except Exception as e:
            logger.warning(f"融合引擎: Redis 保存权重失败 ({e})")

    def _normalize(self):
        """归一化权重，确保总和为 1"""
        total = sum(self._weights.values())
        if total > 0:
            self._weights = {k: v / total for k, v in self._weights.items()}

    # ==================== 准确率追踪 ====================

    def record_accuracy(self, agent_name: str, correct: bool):
        """记录 Agent 的历史预测准确率

        Args:
            agent_name: Agent 名称
            correct: 预测是否正确
        """
        if agent_name not in self._weights:
            logger.warning(f"融合引擎: 未知 Agent '{agent_name}'，跳过准确率记录")
            return
        if not self._redis:
            return
        try:
            key = f"{self.ACCURACY_KEY_PREFIX}{agent_name}"
            self._redis.lpush(key, 1 if correct else 0)
            self._redis.ltrim(key, 0, self.MAX_ACCURACY_RECORDS - 1)
        except Exception as e:
            logger.warning(f"融合引擎: 记录准确率失败 ({e})")

    def get_accuracy(self, agent_name: str) -> Optional[float]:
        """获取 Agent 的历史准确率

        Args:
            agent_name: Agent 名称
        Returns:
            准确率 (0~1), None 表示无数据
        """
        if not self._redis:
            return None
        try:
            key = f"{self.ACCURACY_KEY_PREFIX}{agent_name}"
            records = self._redis.lrange(key, 0, -1)
            if records:
                return sum(int(r) for r in records) / len(records)
        except Exception:
            pass
        return None

    def learn_weights(self):
        """根据历史准确率自动调整权重

        公式: 新权重 = 基础权重 × (0.5 + 准确率)
        准确率范围 0~1, 所以 new_weight 在 [0.5x, 1.5x] 范围内
        最后归一化确保总和为1。
        """
        if not self._redis:
            logger.info("融合引擎: 未配置 Redis，跳过权重学习")
            return

        for agent in list(self._weights.keys()):
            accuracy = self.get_accuracy(agent)
            if accuracy is not None:
                # 准确率 > 0.5 → 权重增加; < 0.5 → 权重减少
                self._weights[agent] *= (0.5 + accuracy)

        self._normalize()
        self._save_weights()
        logger.info(f"融合引擎: 权重学习完成 (基于 {len(self._weights)} 个 Agent 的准确率)")

    # ==================== 权重管理 ====================

    def update_weight(self, agent_name: str, new_weight: float):
        """动态更新某个 Agent 的权重，自动归一化并持久化"""
        if agent_name not in self._weights:
            logger.warning(f"融合引擎: 未知 Agent '{agent_name}'，跳过权重更新")
            return
        self._weights[agent_name] = max(0.0, new_weight)
        self._normalize()
        self._save_weights()
        logger.info(f"融合引擎: 更新 {agent_name} 权重为 {new_weight:.3f}")

    def get_weights(self) -> dict[str, float]:
        """获取当前权重（只读副本）"""
        return dict(self._weights)

    # ==================== 融合逻辑 ====================

    def fuse(self, reports: dict[str, dict]) -> dict:
        """融合多个 Agent 的报告，输出最终决策"""
        if not reports:
            return {"action": "hold", "confidence": 0, "reason": "无可用分析数据"}

        directions, scores, details = [], [], []

        for agent_name, report in reports.items():
            weight = self._weights.get(agent_name, 0.1)
            direction = self._extract_direction(report)
            confidence = self._extract_confidence(report)

            directions.append(direction)
            scores.append(confidence * weight)

            details.append({
                "agent": agent_name,
                "direction": direction,
                "confidence": confidence,
                "weight": round(weight, 3),
                "weighted_score": round(confidence * weight, 3),
            })

        buy_score = sum(s for d, s in zip(directions, scores) if d == "buy")
        sell_score = sum(s for d, s in zip(directions, scores) if d == "sell")
        hold_score = sum(s for d, s in zip(directions, scores) if d == "hold")

        if buy_score > max(sell_score, hold_score):
            final_action = "buy"
            final_confidence = buy_score / sum(self._weights.values())
        elif sell_score > hold_score:
            final_action = "sell"
            final_confidence = sell_score / sum(self._weights.values())
        else:
            final_action = "hold"
            final_confidence = hold_score / sum(self._weights.values())

        return {
            "action": final_action,
            "confidence": round(min(final_confidence, 1.0), 4),
            "buy_score": round(buy_score, 4),
            "sell_score": round(sell_score, 4),
            "hold_score": round(hold_score, 4),
            "agent_details": sorted(details, key=lambda x: x["weighted_score"], reverse=True),
            "stock_code": reports.get(list(reports.keys())[0], {}).get("stock_code", ""),
        }

    @staticmethod
    def _extract_direction(report: dict) -> str:
        decision = report.get("decision", {})
        direction = decision.get("direction", "")
        if direction in ("buy", "sell", "hold"):
            return direction
        analysis = (report.get("analysis") or "").lower()
        if any(kw in analysis for kw in ("买入", "看多", "增持", "recommend_buy")):
            return "buy"
        if any(kw in analysis for kw in ("卖出", "看空", "减持", "recommend_sell")):
            return "sell"
        return "hold"

    @staticmethod
    def _extract_confidence(report: dict) -> float:
        decision = report.get("decision", {})
        confidence = decision.get("confidence", 0.5)
        sentiment = abs(report.get("sentiment_score", 0))
        return min((confidence + sentiment) / 2, 1.0)


fusion_engine = FusionEngine()
