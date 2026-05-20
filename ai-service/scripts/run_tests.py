#!/usr/bin/env python3
"""运行所有测试并输出结果"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(str(Path(__file__).resolve().parent.parent))

import pytest

if __name__ == "__main__":
    exit_code = pytest.main([
        "tests/test_integration.py",
        "-v",
        "--tb=short",
        "--no-header",
    ])
    print(f"\nExit code: {exit_code}")
    sys.exit(exit_code)
