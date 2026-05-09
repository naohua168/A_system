"""
端到端全链路验证脚本
验证: 采集 → 存储 → 后端 → 前端 整条数据管道

用法:
    python scripts/e2e_verify.py              # 全量检查
    python scripts/e2e_verify.py --skip-hdfs  # 跳过 HDFS/Hive 检查
    python scripts/e2e_verify.py --verbose    # 详细输出
"""

import argparse
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))


class E2ETester:
    """端到端链路测试器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: list[dict] = []
        self.errors = 0
        self.passes = 0

    def log(self, msg: str, level: str = "INFO"):
        icon = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "WARN": "⚠️"}
        print(f"  {icon.get(level, '•')} {msg}")

    def check(self, name: str, func, *args, **kwargs):
        """执行一个检查项"""
        result = {"name": name, "status": "PASS", "detail": ""}
        try:
            ret = func(*args, **kwargs)
            if ret is False:
                raise AssertionError("返回 False")
            result["detail"] = str(ret) if ret and ret is not True else ""
            self.passes += 1
        except Exception as e:
            result["status"] = "FAIL"
            result["detail"] = str(e)
            self.errors += 1
        self.results.append(result)
        self.log(f"{name}", level=result["status"])
        if result["detail"] and self.verbose:
            self.log(f"  └─ {result['detail']}", level="INFO")
        return result["status"] == "PASS"

    def print_summary(self):
        total = len(self.results)
        print(f"\n{'='*50}")
        print(f"📊  全链路验证报告")
        print(f"{'='*50}")
        print(f"   总计: {total}  通过: {self.passes}  失败: {self.errors}")
        if self.errors:
            print(f"\n❌ 失败项:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"   • {r['name']}: {r['detail']}")
        else:
            print(f"\n🎉 全部通过！")
        return self.errors == 0

    # ============================================================
    # 检查项
    # ============================================================

    def check_project_structure(self):
        """1. 项目结构完整性"""
        required_dirs = [
            "data-collector", "backend", "frontend",
            "bigdata-processing", "analysis-algorithms",
            "ai-service",
        ]
        for d in required_dirs:
            if not (ROOT / d).exists():
                raise FileNotFoundError(f"缺少目录: {d}")
        return f"项目结构完整 ({', '.join(required_dirs)})"

    def check_data_collector(self):
        """2. 数据采集器可用性"""
        sys.path.insert(0, str(ROOT / "data-collector"))
        from collectors.data_source_factory import DataSourceFactory
        factory = DataSourceFactory()
        sources = factory.list_supported_sources()
        if not sources:
            raise AssertionError("无可用数据源")
        return f"数据源: {', '.join(sources)}"

    def check_python_deps(self):
        """3. Python 依赖检查"""
        required = ["pandas", "numpy"]
        missing = []
        for pkg in required:
            try:
                importlib.import_module(pkg)
            except ImportError:
                missing.append(pkg)
        if missing:
            raise ImportError(f"缺少依赖: {', '.join(missing)}")
        return f"核心依赖就绪 ({', '.join(required)})"

    def check_analysis_algorithms(self):
        """4. 分析算法模块"""
        sys.path.insert(0, str(ROOT / "analysis-algorithms"))
        from technical import MA, MACD
        from chanlun.fractal import merge_klines, find_fractals
        return "缠论 + 技术指标模块可导入"

    def check_backend_api(self):
        """5. 后端 API 可达性"""
        import requests
        try:
            resp = requests.get("http://localhost:8080/api/stock/list",
                                timeout=5, params={"page": 1, "size": 5})
            if resp.status_code == 200:
                data = resp.json()
                return f"后端 API 可达, 返回 {len(data.get('records', data if isinstance(data, list) else []))} 条股票"
            return False
        except requests.ConnectionError:
            raise ConnectionError("后端未启动 (http://localhost:8080)")

    def check_frontend_build(self):
        """6. 前端可构建"""
        result = subprocess.run(
            ["npx", "vue-tsc", "--noEmit"],
            cwd=str(ROOT / "frontend"),
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"TypeScript 错误:\n{result.stderr[:500]}")
        return "TypeScript 编译通过"

    def check_hdfs_connect(self):
        """7. HDFS 连接（可选）"""
        try:
            from hdfs import InsecureClient
            client = InsecureClient("http://localhost:9870", user="hadoop")
            status = client.status("/")
            return f"HDFS 可达, 状态: {status.get('type', '?')}"
        except ImportError:
            raise RuntimeError("hdfs 库未安装")
        except Exception as e:
            raise ConnectionError(f"HDFS 不可达: {e}")

    def check_hive_tables(self):
        """8. Hive 表验证（可选）"""
        try:
            result = subprocess.run(
                ["beeline", "-u", "jdbc:hive2://localhost:10000",
                 "-e", "SHOW TABLES IN stock_analysis;"],
                capture_output=True, text=True, timeout=30,
            )
            if "stock_basic" in result.stdout or "stock_daily" in result.stdout:
                return "Hive 表已创建"
            raise AssertionError("Hive 表未找到")
        except FileNotFoundError:
            raise RuntimeError("beeline 未安装")

    def check_ai_service(self):
        """9. AI 对话服务模块"""
        ai_root = ROOT / "ai-service"
        if not ai_root.exists():
            raise FileNotFoundError("ai-service 目录不存在")
        required_files = [
            "app/main.py", "app/config.py", "app/api/dialogue.py",
            "app/models/deepseek_client.py", "app/services/dialogue_service.py",
            "requirements.txt",
        ]
        for f in required_files:
            if not (ai_root / f).exists():
                raise FileNotFoundError(f"缺少文件: ai-service/{f}")
        return "AI 服务模块完整"

    def check_ai_backend_controller(self):
        """10. 后端 AI 控制器"""
        controller = ROOT / "backend/src/main/java/com/stock/controller/AiDialogueController.java"
        if not controller.exists():
            raise FileNotFoundError("缺少 AiDialogueController.java")
        return "后端 AI 控制器就绪"

    def check_ai_frontend_page(self):
        """11. 前端 AI 对话页面"""
        chat_view = ROOT / "frontend/src/views/ChatView.vue"
        api_ai = ROOT / "frontend/src/api/ai.ts"
        if not chat_view.exists():
            raise FileNotFoundError("缺少 ChatView.vue")
        if not api_ai.exists():
            raise FileNotFoundError("缺少 api/ai.ts")
        content = chat_view.read_text(encoding="utf-8")
        if "占位页面" in content or "此功能正在开发中" in content:
            raise AssertionError("ChatView.vue 仍是占位页面，未完成开发")
        return "前端 AI 对话页面就绪"


def main():
    parser = argparse.ArgumentParser(description="端到端全链路验证")
    parser.add_argument("--skip-hdfs", action="store_true", help="跳过 HDFS/Hive 检查")
    parser.add_argument("--skip-backend", action="store_true", help="跳过后端 API 检查")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    tester = E2ETester(verbose=args.verbose)

    print("=" * 50)
    print("🔗  全链路端到端验证")
    print(f"   项目根目录: {ROOT}")
    print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # ------ 链1: 项目结构 ------
    print("\n📁 1. 项目结构")
    tester.check("项目目录完整性", tester.check_project_structure)

    # ------ 链2: 数据采集 ------
    print("\n📡 2. 数据采集层")
    tester.check("Python 核心依赖", tester.check_python_deps)
    tester.check("数据源工厂", tester.check_data_collector)
    tester.check("分析算法模块", tester.check_analysis_algorithms)

    # ------ 链3: 后端 ------
    if not args.skip_backend:
        print("\n🔙 3. 后端服务")
        tester.check("后端 API", tester.check_backend_api)

    # ------ 链4: 前端 ------
    print("\n🎨 4. 前端")
    tester.check("TypeScript 编译", tester.check_frontend_build)

    # ------ 链5: AI 服务 ------
    print("\n🤖 5. AI 对话服务")
    tester.check("AI 服务模块", tester.check_ai_service)
    tester.check("后端 AI 控制器", tester.check_ai_backend_controller)
    tester.check("前端 AI 对话页面", tester.check_ai_frontend_page)

    # ------ 链6: HDFS/Hive ------
    if not args.skip_hdfs:
        print("\n💾 5. 大数据存储")
        tester.check("HDFS 连接", tester.check_hdfs_connect)
        tester.check("Hive 表", tester.check_hive_tables)

    # ------ 报告 ------
    return 0 if tester.print_summary() else 1


if __name__ == "__main__":
    sys.exit(main())
