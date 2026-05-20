"""通用 AI 大模型客户端（支持 DeepSeek / OpenAI 兼容协议）"""
import json
import httpx
from loguru import logger
from typing import Optional

from app.config import settings
from app.models.simulation import get_mock_data, select_dialog_template, DIALOG_TEMPLATES

# ── 股市分析系统提示词 ──
SYSTEM_PROMPT = """你是一位专业的股市分析专家，擅长股票基金技术分析。
你能回答的问题包括：
1. 股票/基金行情分析：K线形态、趋势判断、支撑位/压力位
2. 技术指标解读：MA、MACD、KDJ、RSI、布林带等
3. 缠论分析：分型、笔、线段、中枢、买卖点
4. 行业板块分析：热点追踪、轮动判断
5. 投资策略建议：均线策略、趋势跟踪、风险控制

回答要求：
- 基于技术分析给出客观判断，不承诺收益
- 提及具体的技术指标数值作为论据
- 提示风险，说明分析仅供参考
- 回答简洁专业，控制在200-500字"""

# ── 向后兼容导出（新代码建议从 simulation 导入） ──
MOCK_RESPONSES = DIALOG_TEMPLATES
MOCK_TEMPLATES = DIALOG_TEMPLATES


class AIClient:
    """AI 大模型客户端（支持 SiliconFlow / DeepSeek 双后端）

    优先级:
      1. SILICONFLOW_API_KEY（已配置）→ SiliconFlow（OpenAI 兼容协议）
      2. DEEPSEEK_API_KEY（已配置）    → DeepSeek API
      3. 均未配置                        → 模拟模式（中文模板回复）
    """

    def __init__(self):
        # 优先使用 SiliconFlow（已在 .env 中配置）
        if settings.siliconflow_api_key:
            self.api_key = settings.siliconflow_api_key
            self.api_url = settings.siliconflow_api_url
            self.model = settings.siliconflow_model
            self.backend = "siliconflow"
            self.mock_mode = False
            logger.info(f"✅ 已连接硅基流动 API (模型: {self.model})")
        elif settings.deepseek_api_key:
            self.api_key = settings.deepseek_api_key
            self.api_url = settings.deepseek_api_url
            self.model = settings.deepseek_model
            self.backend = "deepseek"
            self.mock_mode = False
            logger.info(f"✅ 已连接 DeepSeek API (模型: {self.model})")
        else:
            self.api_key = ""
            self.api_url = ""
            self.model = "mock"
            self.backend = "mock"
            self.mock_mode = True
            logger.warning("⚠️ 未配置 AI API Key，将使用模拟回复模式")

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """发送对话请求（真实 API 失败时自动降级到模拟回复）"""
        if self.mock_mode:
            return self._mock_reply(messages)
        return await self._real_chat(messages, temperature, max_tokens)

    async def _real_chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        """调用真实 API（兼容 OpenAI 协议的所有端点）"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.9,
                }
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                resp = await client.post(self.api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"AI API 调用失败 ({self.backend}): {e}")
            return self._mock_reply(messages)

    def _mock_reply(self, messages: list[dict]) -> str:
        """模拟回复（使用统一模板）"""
        last_msg = messages[-1]["content"] if messages else ""
        template = select_dialog_template(last_msg)
        data = get_mock_data(last_msg)
        try:
            return template.format(**data)
        except KeyError:
            return MOCK_TEMPLATES["general_advice"].format(query=last_msg, **get_mock_data(last_msg))

    @property
    def status(self) -> dict:
        if self.mock_mode:
            return {
                "mode": "mock",
                "model": "mock",
                "backend": "mock",
                "api_configured": False,
                "hint": "配置 SILICONFLOW_API_KEY 或 DEEPSEEK_API_KEY 环境变量可使用真实 AI 模型",
            }
        return {
            "mode": "real",
            "model": self.model,
            "backend": self.backend,
            "api_configured": True,
            "hint": f"已连接 {self.backend} API",
        }


client = AIClient()
