#!/usr/bin/env python3
"""
硅基流动 API 调用测试 — 验证 L5 优化功能
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def run_tests():
    """运行所有硅基流动测试"""
    from tests.test_siliconflow_core import run_all
    return await run_all()


def main():
    """同步入口"""
    results = asyncio.run(run_tests())
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"📊 测试结果汇总")
    print(f"{'='*60}")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\n📈 通过: {passed}/{total} ({passed/total*100:.0f}%)")
    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
