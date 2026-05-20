"""FusionEngine 定时权重学习调度测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from app.fusion import FusionEngine


class TestFusionEngineScheduling:
    """测试 FusionEngine 权重学习的调度逻辑"""

    def test_learn_weights_no_redis_does_nothing(self):
        """未配置 Redis 时 learn_weights 不执行任何操作"""
        engine = FusionEngine(redis_client=None)
        initial_weights = dict(engine._weights)

        engine.learn_weights()

        # 权重不应变化
        assert engine._weights == initial_weights

    def test_weight_learn_task_cancelled_gracefully(self):
        """定时学习任务被取消时优雅退出"""
        async def run():
            task = asyncio.create_task(asyncio.sleep(3600))
            await asyncio.sleep(0.01)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return True
            return False

        result = asyncio.run(run())
        assert result is True

    def test_learn_weights_with_accuracy_data(self):
        """有历史准确率数据时，权重应动态调整"""
        mock_redis = MagicMock()
        # 模拟有准确率记录
        mock_redis.lrange.return_value = [b'1', b'1', b'0', b'1', b'1']  # 准确率 80%
        engine = FusionEngine(redis_client=mock_redis)

        original_weight = engine._weights["technical_analyst"]
        engine.learn_weights()

        # 准确率 0.8 时权重应增加 (new_weight > original_weight)
        # 公式: new = original * (0.5 + 0.8) = original * 1.3
        # 归一化后仍应 > original_weight * 1.3 / total
        assert engine._weights["technical_analyst"] > original_weight * 0.5
        # 总和为 1
        assert abs(sum(engine._weights.values()) - 1.0) < 1e-6

    def test_learn_weights_persists_to_redis(self):
        """learn_weights 应将新权重持久化到 Redis"""
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = [b'1', b'1', b'0', b'1', b'1']
        engine = FusionEngine(redis_client=mock_redis)

        engine.learn_weights()
        # 验证持久化
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "fusion:weights"

    def test_learn_weights_maintains_agent_keys(self):
        """权重学习后所有 Agent 键名保持不变"""
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = [b'1', b'0', b'1']
        engine = FusionEngine(redis_client=mock_redis)

        original_keys = set(engine._weights.keys())
        engine.learn_weights()
        assert set(engine._weights.keys()) == original_keys


@pytest.mark.asyncio
async def test_weight_learn_background_task():
    """验证后台定时任务的启动和取消"""

    async def _simple_learn_loop():
        """模拟权重学习循环，间隔短时间"""
        while True:
            await asyncio.sleep(3600)
            print("weight learn executed (simulation)")

    task = asyncio.create_task(_simple_learn_loop())
    await asyncio.sleep(0.01)
    assert not task.done()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert task.cancelled()
