#!/usr/bin/env python3
"""
L5 AI 智能服务层优化脚本
=====================
使用硅基流动 (SiliconFlow) 大语言模型 API 对 L5 层进行智能优化分析。

基于以下文件源码进行分析并生成优化方案：
- app/agents/*.py        -> Agent 架构与 Prompt 优化
- app/services/*.py      -> 服务逻辑优化
- app/models/*.py        -> 模型调用优化
- app/fusion/*.py        -> 融合引擎优化
- app/api/dialogue.py    -> API 层优化
- app/config.py          -> 配置优化

使用方式：
    python scripts/optimize_l5.py                    # 完整分析
    python scripts/optimize_l5.py --all              # 完整分析
    python scripts/optimize_l5.py --category prompt  # 仅 Prompt 优化
    python scripts/optimize_l5.py --category agent   # 仅 Agent 优化
    python scripts/optimize_l5.py --output report.md # 输出到文件
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# 配置硅基流动 API — 优先从环境变量读取
import os
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")

# ── L5 优化的系统级 Prompt ──
L5_SYSTEM_PROMPT = """你是一位顶级的 AI 系统架构师和金融量化平台专家。
你的任务是对"基金股票智能分析系统"的 L5 (AI 智能服务层) 进行全面优化分析。

## 系统背景
这是一个六层架构的金融智能分析平台:
- L1: 数据采集层 (Python)
- L2: 大数据处理层 (Hive+Spark+MapReduce)
- L3: 算法分析层 (Python 技术指标+缠论+量化)
- L4: 后端 API 层 (Spring Boot 3)
- L5: AI 智能服务层 (FastAPI+多智能体) ← 当前焦点
- L6: 前端展示层 (Vue 3)

## L5 层当前架构
L5 基于 FastAPI + 多智能体架构:
- 7 个专业化 Agent (顺序执行或并行)
- DeepSeek API / 模拟回复双模式
- Redis 记忆服务 + 文件降级
- 多模型注册中心 + 故障转移

## 优化要求
请基于下方提供的源码，从以下维度给出 **具体、可执行、有代码示例** 的优化方案：

### 1. Prompt 工程优化 (P0)
- 改进各 Agent 的 system_prompt，注入 Chain-of-Thought 引导
- 添加 Few-shot 示例提升输出质量
- 设计结构化输出格式约束

### 2. 多智能体协作优化 (P0)
- 改进 Agent 间信息传递机制
- 优化研究员辩论流程 (串联 vs 并联)
- 增强融合引擎的加权策略

### 3. 后端集成纠正 (P0)
- 修复各 Agent 中调用后端 API 的路径错误
- 确保路径与 L4 实际提供的 REST API 一致
- 添加重试和降级策略

### 4. 功能增强 (P1)
- 增加 SSE 流式输出支持
- 暴露多智能体分析 API 接口
- 集成 FusionEngine 到主流程

### 5. Agent 决策逻辑优化 (P1)
- TraderAgent 动态计算仓位/止损
- RiskManager 基于真实数据评估
- 修复 ResearcherTeam 的硬编码问题

### 6. 整体架构改进 (P2)
- 统一错误处理
- 增强日志与监控
- 性能优化建议

## 输出格式
请以结构化标记输出，包含优化方案清单（每个优化项含：优先级、当前问题、优化方案、代码实现）。"""


def read_source_files() -> dict:
    """读取 L5 层所有核心源码文件"""
    app_dir = PROJECT_ROOT / "app"
    files = {}
    
    # 递归扫描所有 .py 文件
    for py_file in sorted(app_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        try:
            rel_path = str(py_file.relative_to(PROJECT_ROOT))
            content = py_file.read_text(encoding="utf-8")
            files[rel_path] = content
        except Exception as e:
            files[str(py_file.relative_to(PROJECT_ROOT))] = f"# 读取失败: {e}"
    
    return files


def build_analysis_prompt(source_files: dict, category: str = "all") -> str:
    """构建分析 Prompt — 包含当前代码上下文"""
    prompt_parts = [
        "# L5 AI 智能服务层 源码分析",
        "",
        "请基于以下完整的 L5 层源码，提供深度的优化方案。",
        "",
    ]
    
    # 按目录分组展示文件
    categories = {
        "agents": [k for k in source_files if k.startswith("app/agents/")],
        "services": [k for k in source_files if k.startswith("app/services/")],
        "models": [k for k in source_files if k.startswith("app/models/")],
        "fusion": [k for k in source_files if k.startswith("app/fusion/")],
        "api": [k for k in source_files if k.startswith("app/api/")],
        "core": [k for k in source_files if k in ("app/config.py", "app/main.py")],
        "utils": [k for k in source_files if k.startswith("app/utils/")],
    }
    
    for section_name, file_list in categories.items():
        if not file_list:
            continue
        prompt_parts.append(f"\n## {section_name.upper()}/")
        for fp in file_list:
            content = source_files[fp]
            prompt_parts.append(f"\n### 📄 {fp}")
            prompt_parts.append("```python")
            prompt_parts.append(content)
            prompt_parts.append("```")
    
    # 添加优化方向指引
    prompt_parts.append(f"""
---
## 优化方向

请针对以下 {category if category != 'all' else '全部'} 方面进行优化分析：

### 如果 category == 'all'，请涵盖：
1. **Prompt 工程优化** — 改进 Agent 提示词设计、CoT 引导
2. **多智能体协作** — Agent 间信息共享、辩论流程、融合策略
3. **后端集成修复** — 修正所有后端 API 调用路径错误
4. **功能增强** — SSE 流式输出、API 暴露、FusionEngine 集成
5. **Agent 逻辑优化** — TraderAgent/RiskManager 动态决策
6. **架构改进** — 错误处理、日志、监控、性能

请为每个优化项提供：
- **优化项ID**: 唯一标识
- **优先级**: P0/P1/P2
- **当前问题**: 具体问题描述
- **优化方案**: 详细方案
- **代码示例**: 可直接使用的 Python 代码
- **预期收益**: 优化后提升效果
""")
    
    return "\n".join(prompt_parts)


async def call_siliconflow_api(prompt: str, model: str = "Qwen/Qwen2.5-72B-Instruct") -> str:
    """调用硅基流动 API"""
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": L5_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,  # 低温度保证输出稳定
        "max_tokens": 8192,
        "top_p": 0.9,
        "stream": False,
    }
    
    url = "https://api.siliconflow.cn/v1/chat/completions"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as client:
                print(f"📡 正在请求硅基流动 API ({model})... 尝试 {attempt + 1}/{max_retries}")
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # 记录 Token 用量
                usage = data.get("usage", {})
                print(f"✅ API 调用成功 | 输入: {usage.get('prompt_tokens', '?')} tokens | "
                      f"输出: {usage.get('completion_tokens', '?')} tokens")
                
                return data["choices"][0]["message"]["content"]
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP 错误 ({e.response.status_code}): {e.response.text[:200]}")
            if e.response.status_code == 401:
                raise ValueError("API Key 无效！请检查 SILICONFLOW_API_KEY 配置")
            if e.response.status_code == 429:
                print("⏳ 触发限流, 等待后重试...")
                await asyncio.sleep(2 ** attempt)
            elif attempt == max_retries - 1:
                raise
        except httpx.TimeoutException:
            print(f"⏰ 请求超时 (尝试 {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise TimeoutError("API 请求超时，请稍后重试")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            print(f"❌ API 调用失败: {e}")
            if attempt == max_retries - 1:
                raise
    
    return ""


def save_report(report_content: str, output_path: Optional[Path] = None) -> Path:
    """保存优化报告到文件"""
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = PROJECT_ROOT / "logs" / f"l5_optimization_report_{timestamp}.md"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding="utf-8")
    print(f"\n📝 优化报告已保存至: {output_path}")
    return output_path


async def main():
    """主入口"""
    print("=" * 60)
    print("  L5 AI 智能服务层 — 硅基流动 AI 优化引擎")
    print("=" * 60)
    print()
    
    # 解析参数
    category = "all"
    output_path = None
    model = "Qwen/Qwen2.5-72B-Instruct"
    
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            category = sys.argv[idx + 1]
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])
    
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]
    
    # 1. 读取源码
    print("📖 正在读取 L5 层源码...")
    source_files = read_source_files()
    print(f"   共读取 {len(source_files)} 个源文件:")
    for fp in source_files:
        size = len(source_files[fp])
        print(f"   ├ {fp} ({size} bytes)")
    
    # 2. 构建 Prompt
    print(f"\n🧠 正在构建分析 Prompt (优化维度: {category})...")
    prompt = build_analysis_prompt(source_files, category)
    prompt_tokens = len(prompt) // 4  # 粗略估算 token 数
    print(f"   Prompt 长度: {len(prompt)} 字符 (约 {prompt_tokens} tokens)")
    
    # 3. 调用 API
    print(f"\n🚀 开始调用硅基流动 API...")
    start_time = datetime.now()
    
    try:
        report = await call_siliconflow_api(prompt, model)
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n⏱ 总耗时: {elapsed:.1f}s")
        
        # 4. 构建完整报告
        full_report = f"""# L5 AI 智能服务层 优化报告

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 使用模型: {model}
> 优化维度: {category}
> 分析源文件: {len(source_files)} 个
> API 提供商: 硅基流动 (SiliconFlow)

---

{report}

---

*本报告由 L5 优化引擎通过硅基流动 API 自动生成。*
"""
        
        # 5. 保存报告
        saved_path = save_report(full_report, output_path)
        
        # 6. 输出摘要
        lines = report.strip().split("\n")
        print(f"\n📊 报告摘要:")
        print(f"   源文件: {len(source_files)} 个")
        print(f"   报告行数: {len(lines)} 行")
        print(f"   报告文件: {saved_path}")
        print(f"\n🔍 建议执行: type {saved_path}  |  cat {saved_path}")
        
        return full_report
        
    except Exception as e:
        print(f"\n❌ 优化分析失败: {e}")
        return f"# L5 优化失败\n\n**错误**: {e}\n**时间**: {datetime.now()}\n"


if __name__ == "__main__":
    asyncio.run(main())
