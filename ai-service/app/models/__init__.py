"""AI 模型客户端"""
from app.models.deepseek_client import AIClient, client, MOCK_TEMPLATES, MOCK_RESPONSES
from app.models.model_registry import ModelRegistry
from app.models.simulation import SimulationEngine, DIALOG_TEMPLATES, AGENT_TEMPLATES
from app.models.siliconflow_client import (
    SiliconFlowClient,
    SiliconFlowConfig,
    siliconflow_client,
    init_siliconflow_client,
    optimize_l5_with_siliconflow,
)

__all__ = [
    "AIClient", "client", "MOCK_TEMPLATES", "MOCK_RESPONSES",
    "ModelRegistry",
    "SimulationEngine", "SIMULATION_TEMPLATES",
    "SiliconFlowClient", "SiliconFlowConfig",
    "siliconflow_client", "init_siliconflow_client",
    "optimize_l5_with_siliconflow",
]
