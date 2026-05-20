"""硅基流动 (SiliconFlow) API 客户端 - 优化 L5 AI 服务"""
import json
import httpx
from loguru import logger
from typing import Optional, AsyncGenerator
from dataclasses import dataclass

from app.config import settings


@dataclass
class SiliconFlowConfig:
    """硅基流动 API 配置"""
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Qwen/Qwen2.5-72B-Instruct"  # 默认使用 Qwen2.5-72B
    timeout: float = 60.0
    max_retries: int = 3


# L5 优化专用系统提示词
L5_OPTIMIZATION_SYSTEM_PROMPT = """你是一位专业的 AI 系统架构师和 Prompt Engineering 专家。
你的任务是对基金股票智能分析系统的 L5 (AI 智能服务层) 进行深度优化。

## L5 层现状
当前 L5 层基于 FastAPI + 多智能体架构，包含：
1. 7 个专业化 Agent（基本面/技术面/情绪/新闻/辩论/交易/风控）
2. 多模型支持（DeepSeek / SiliconFlow 等）
3. 记忆服务（Redis + 文件降级）
4. 模拟降级模式（无 API Key 时使用）

## 优化维度
请从以下维度提供优化建议：

### 1. Prompt 工程优化
- 各 Agent 的系统提示词精细化
- Few-shot 示例设计
- Chain-of-Thought 引导

### 2. 多智能体协作优化
- Agent 间的信息共享机制
- 辩论流程的迭代优化
- 结果融合策略改进

### 3. 性能优化
- 响应延迟优化方案
- Token 使用效率提升
- 缓存策略建议

### 4. 功能增强
- 缺失的功能模块建议
- 错误处理改进
- 日志与监控增强

## 输出格式
请以结构化 JSON 格式输出优化建议，包含：
- optimization_id: 优化项唯一标识
- category: 优化类别 (prompt/agent/performance/feature)
- priority: 优先级 (P0/P1/P2)
- current_issue: 当前问题描述
- optimized_solution: 优化方案详情
- expected_benefit: 预期收益
- implementation_code: 可执行的代码示例

请确保建议具体、可落地、代码可直接使用。"""


class SiliconFlowClient:
    """硅基流动 API 客户端"""

    # 支持的模型列表
    AVAILABLE_MODELS = [
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1",
        "THUDM/glm-4-9b-chat",
        "meta-llama/Meta-Llama-3.1-70B-Instruct",
    ]

    def __init__(self, config: Optional[SiliconFlowConfig] = None):
        self.config = config or SiliconFlowConfig()
        self.api_key = self.config.api_key or getattr(settings, 'siliconflow_api_key', '')
        self.base_url = self.config.base_url.rstrip('/')
        self.model = self.config.model
        self.timeout = self.config.timeout
        self.max_retries = self.config.max_retries
        
        # 请求头构建
        self.headers = self._build_headers()
        
        # 状态追踪
        self._last_usage = {}
        self._request_count = 0

    def _build_headers(self) -> dict:
        """构建 API 请求头"""
        if not self.api_key:
            raise ValueError("硅基流动 API Key 未配置")
        
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_request_payload(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[list] = None,
    ) -> dict:
        """构建请求体"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        return payload

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """非流式对话"""
        payload = self._build_request_payload(messages, temperature, max_tokens, stream=False)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # 记录用量
                    self._last_usage = data.get("usage", {})
                    self._request_count += 1
                    
                    return data["choices"][0]["message"]["content"]
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"硅基流动 API HTTP 错误 (尝试 {attempt + 1}/{self.max_retries}): {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 401:
                    raise ValueError("API Key 无效或已过期") from e
                elif e.response.status_code == 429:
                    logger.warning("请求过于频繁，等待重试...")
                    await self._exponential_backoff(attempt)
                elif attempt == self.max_retries - 1:
                    raise
                    
            except httpx.TimeoutException as e:
                logger.error(f"硅基流动 API 超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise TimeoutError("API 请求超时，请稍后重试") from e
                await self._exponential_backoff(attempt)
                
            except Exception as e:
                logger.error(f"硅基流动 API 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"API 调用失败: {e}") from e
                await self._exponential_backoff(attempt)
        
        return ""

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """流式对话 (SSE)"""
        payload = self._build_request_payload(messages, temperature, max_tokens, stream=True)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]  # 去掉 "data: " 前缀
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            logger.error(f"流式 API 调用失败: {e}")
            raise

    async def optimize_l5_layer(self, current_code: str = "") -> dict:
        """专门用于优化 L5 AI 层的分析"""
        messages = [
            {"role": "system", "content": L5_OPTIMIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_l5_analysis_prompt(current_code)}
        ]
        
        response = await self.chat(messages, temperature=0.3, max_tokens=4096)
        
        # 尝试解析 JSON 响应
        try:
            # 提取 JSON 部分（可能被 markdown 代码块包裹）
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("API 返回非 JSON 格式，返回原始文本")
            return {
                "raw_response": response,
                "parsed": False
            }

    def _build_l5_analysis_prompt(self, current_code: str = "") -> str:
        """构建 L5 分析 Prompt"""
        prompt = """请分析以下 L5 AI 服务层的代码结构，并提供详细的优化方案：

## 当前 L5 层核心代码结构

### 1. 多智能体架构 (app/agents/)
- base_agent.py: 抽象基类，定义 chat/analyze 接口
- fundamentals_analyst.py: 基本面分析 (PE/PB/市值)
- technical_analyst.py: 技术分析 (MA/MACD/KDJ/RSI/布林带)
- sentiment_analyst.py: 情绪分析 (题材/龙虎榜/北向)
- news_analyst.py: 新闻分析 (新闻情绪/事件影响)
- researcher_team.py: 研究员辩论 (看涨vs看跌3轮)
- trader_agent.py: 交易决策 (方向/仓位/止损)
- risk_manager.py: 风控审核 (风险评级/最终裁定)

### 2. 核心服务 (app/services/)
- dialogue_service.py: 对话服务，注入实时数据上下文
- multi_agent_service.py: 多智能体编排引擎
- memory_service.py: 记忆持久化 (Redis+文件)

### 3. 模型层 (app/models/)
- deepseek_client.py: DeepSeek API 客户端
- model_registry.py: 多模型注册中心
- simulation.py: 模拟降级引擎

### 4. 已知问题
1. Agent 调用后端 API 路径错误
2. 只有基本对话接口暴露，多智能体/融合功能未暴露
3. FusionEngine 已实现但未被使用
4. 缺少 SSE 流式输出
5. Agent 实现偏简单，有硬编码逻辑

请提供详细的优化方案，包括具体的代码实现。"""

        if current_code:
            prompt += f"\n\n## 当前代码片段\n```python\n{current_code}\n```"
        
        return prompt

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        # 尝试匹配 markdown 代码块
        import re
        
        # 匹配 ```json ... ```
        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # 匹配 [ 开头 ] 结尾 或 { 开头 } 结尾
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if json_match:
            return json_match.group(1).strip()
        
        return text.strip()

    async def _exponential_backoff(self, attempt: int, base_delay: float = 1.0):
        """指数退避重试"""
        import asyncio
        delay = base_delay * (2 ** attempt)
        logger.info(f"等待 {delay} 秒后重试...")
        await asyncio.sleep(delay)

    @property
    def status(self) -> dict:
        """获取客户端状态"""
        return {
            "provider": "siliconflow",
            "model": self.model,
            "api_configured": bool(self.api_key),
            "base_url": self.base_url,
            "request_count": self._request_count,
            "last_usage": self._last_usage,
        }

    def switch_model(self, model_name: str):
        """切换模型"""
        if model_name not in self.AVAILABLE_MODELS:
            logger.warning(f"模型 {model_name} 不在推荐列表中，但仍将尝试使用")
        self.model = model_name
        logger.info(f"已切换至模型: {model_name}")


# 全局客户端实例
siliconflow_client: Optional[SiliconFlowClient] = None


def init_siliconflow_client(api_key: Optional[str] = None) -> SiliconFlowClient:
    """初始化硅基流动客户端"""
    global siliconflow_client
    
    import os
    resolved_key = api_key or os.environ.get("SILICONFLOW_API_KEY", "") or getattr(settings, 'siliconflow_api_key', '')
    if not resolved_key:
        raise ValueError("SILICONFLOW_API_KEY 未配置，请设置环境变量或 .env 文件")
    
    config = SiliconFlowConfig(
        api_key=resolved_key,
        model="Qwen/Qwen2.5-72B-Instruct",
    )
    
    siliconflow_client = SiliconFlowClient(config)
    logger.info("硅基流动客户端初始化完成")
    return siliconflow_client


async def optimize_l5_with_siliconflow(
    api_key: str = "",
    current_code: str = ""
) -> dict:
    """使用硅基流动 API 优化 L5 层的主入口函数"""
    client = init_siliconflow_client(api_key)
    
    try:
        logger.info("开始调用硅基流动 API 优化 L5 层...")
        result = await client.optimize_l5_layer(current_code)
        logger.info("L5 优化分析完成")
        return {
            "success": True,
            "client_status": client.status,
            "optimization_result": result,
        }
    except Exception as e:
        logger.error(f"L5 优化失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


# 用于直接运行的测试代码
if __name__ == "__main__":
    import asyncio
    
    async def main():
        result = await optimize_l5_with_siliconflow()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    asyncio.run(main())
