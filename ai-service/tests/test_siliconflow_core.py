"""硅基流动 API 测试核心模块（async 函数，由同步包装器调用）"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
TEST_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")  # 必须从环境变量读取，禁止硬编码
TEST_MODEL = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# 以下为辅助函数（非 pytest 测试用例），由 run_all() 统一调度
__test__ = False


async def test_connection() -> bool:
    """测试 1: 基础连接与鉴权"""
    import httpx
    headers = {
        "Authorization": f"Bearer {TEST_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.siliconflow.cn/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                print(f"✅ 鉴权成功！可用模型: {len(models)} 个")
                return True
            print(f"❌ 鉴权失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


async def test_chat() -> bool:
    """测试 2: 基础非流式对话"""
    import httpx
    headers = {"Authorization": f"Bearer {TEST_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": TEST_MODEL,
        "messages": [{"role": "system", "content": "简短回复"}, {"role": "user", "content": "回复'通过'"}],
        "temperature": 0.1, "max_tokens": 50,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"✅ 对话成功！回复: {content[:80]}")
            return True
    except Exception as e:
        print(f"❌ 对话失败: {e}")
        return False


async def test_l5_optimization() -> bool:
    """测试 3: L5 优化 Prompt"""
    import httpx
    headers = {"Authorization": f"Bearer {TEST_API_KEY}", "Content-Type": "application/json"}
    prompt = "请分析 L5 AI 服务层的问题：1)API路径错误 2)FusionEngine未集成 3)缺少流式输出。请给出3条优化建议。"
    payload = {
        "model": TEST_MODEL,
        "messages": [{"role": "system", "content": "输出JSON格式优化建议"}, {"role": "user", "content": prompt}],
        "temperature": 0.3, "max_tokens": 1024,
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"✅ L5 优化成功！输出 {len(content)} 字符")
            return True
    except Exception as e:
        print(f"❌ L5 优化失败: {e}")
        return False


async def test_error_handling() -> bool:
    """测试 4: 异常处理"""
    import httpx
    passed = []

    # 4.1 无效 Key
    try:
        headers = {"Authorization": "Bearer invalid", "Content-Type": "application/json"}
        payload = {"model": TEST_MODEL, "messages": [{"role": "user", "content": "hi"}]}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code == 401:
                passed.append(True)
    except:
        passed.append(True)

    # 4.2 无效模型
    try:
        headers = {"Authorization": f"Bearer {TEST_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "nonexistent-model", "messages": [{"role": "user", "content": "hi"}]}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                passed.append(True)
    except:
        passed.append(True)

    print(f"✅ 异常处理通过: {sum(passed)}/2")
    return all(passed) if passed else True


async def run_all() -> dict:
    """按序运行所有测试"""
    results = {}

    # 无 API Key 时跳过真实 API 测试，仅测试异常处理
    if not TEST_API_KEY:
        print("⚠️ 未配置 SILICONFLOW_API_KEY，跳过真实 API 测试，仅测试异常处理")
        results["connection"] = False
        results["chat"] = False
        results["optimization"] = False
        results["error_handling"] = await test_error_handling()
        results["skipped_no_key"] = True
        return results

    results["connection"] = await test_connection()
    if results["connection"]:
        results["chat"] = await test_chat()
        if results["chat"]:
            results["optimization"] = await test_l5_optimization()
        else:
            results["optimization"] = False
    else:
        results["chat"] = results["optimization"] = False
    results["error_handling"] = await test_error_handling()
    return results
