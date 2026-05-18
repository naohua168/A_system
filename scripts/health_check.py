"""
系统健康检查 — 监控数据采集层、大数据处理层、算法分析层运行状态

输出结构化 JSON 报告 + 终端摘要，包含各层状态、检测指标、异常原因。

用法:
    python scripts/health_check.py                  # 全量检查
    python scripts/health_check.py --json            # JSON 格式输出
    python scripts/health_check.py --watch 30        # 每30秒持续监控
    python scripts/health_check.py --layer collector  # 仅检查采集层
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_COLLECTOR_DIR = PROJECT_ROOT / "data-collector"
ANALYSIS_DIR = PROJECT_ROOT / "analysis-algorithms"


# ============================================================
# 状态码
# ============================================================
STATUS_OK = "available"
STATUS_DEGRADED = "degraded"
STATUS_UNAVAILABLE = "unavailable"


# ============================================================
# 基础检测工具
# ============================================================
def _run(cmd: list, timeout: int = 15) -> Tuple[int, str]:
    """执行命令并返回 (exit_code, output)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return -1, "命令未找到"
    except subprocess.TimeoutExpired:
        return -2, "超时"
    except Exception as e:
        return -3, str(e)


def _check_port(host: str, port: int, timeout: int = 3) -> bool:
    """检测 TCP 端口是否可达"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((host, port))
        s.close()
        return r == 0
    except Exception:
        return False


def _http_get(url: str, timeout: int = 5) -> Tuple[int, str]:
    """HTTP GET 请求 — 使用 urllib 避免 PowerShell curl 别名干扰"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=timeout)
        body = r.read().decode("utf-8", errors="replace")
        return r.status, body[:300]
    except Exception as e:
        msg = str(e)
        if isinstance(e, urllib.request.URLError):
            msg = f"URLError: {e.reason}"
        return 0, msg


# ============================================================
# 检测指标定义
# ============================================================
class HealthCheck:
    """系统健康检查器"""

    def __init__(self):
        self.results: Dict[str, dict] = {
            "meta": {
                "check_time": datetime.now().isoformat(),
                "python_version": sys.version.split()[0],
                "project_root": str(PROJECT_ROOT),
            },
            "data_collector_layer": {"status": STATUS_UNAVAILABLE, "components": {}},
            "bigdata_layer": {"status": STATUS_UNAVAILABLE, "components": {}},
            "analysis_layer": {"status": STATUS_UNAVAILABLE, "components": {}},
            "infrastructure": {"status": STATUS_UNAVAILABLE, "components": {}},
        }
        self._failed = 0
        self._total = 0

    def _record(self, layer: str, component: str, status: str,
                detail: str = "", metrics: dict = None) -> dict:
        """记录检测结果"""
        self._total += 1
        entry = {
            "status": status,
            "detail": detail,
            "check_time": datetime.now().isoformat(),
            "metrics": metrics or {},
        }
        self.results[layer]["components"][component] = entry
        if status != STATUS_OK:
            self._failed += 1
        return entry

    def _update_layer_status(self, layer: str):
        """根据子组件状态计算层状态"""
        components = self.results[layer]["components"]
        if not components:
            return
        statuses = [c["status"] for c in components.values()]
        if all(s == STATUS_OK for s in statuses):
            self.results[layer]["status"] = STATUS_OK
        elif any(s == STATUS_UNAVAILABLE for s in statuses):
            self.results[layer]["status"] = STATUS_UNAVAILABLE
        else:
            self.results[layer]["status"] = STATUS_DEGRADED

    # ============================================================
    # 基础设施检测
    # ============================================================

    def check_infrastructure(self):
        """Docker 容器 + 网络基础"""
        # Docker 引擎
        rc, ver = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
        self._record("infrastructure", "docker_engine",
                      STATUS_OK if rc == 0 else STATUS_UNAVAILABLE,
                      f"Docker v{ver}" if rc == 0 else f"不可达: {ver}",
                      {"version": ver})

        # Docker Compose
        rc, ver = _run(["docker", "compose", "version", "--short"])
        self._record("infrastructure", "docker_compose",
                      STATUS_OK if rc == 0 else STATUS_UNAVAILABLE,
                      f"Compose v{ver}" if rc == 0 else f"不可达: {ver}")

        # 容器列表
        rc, output = _run(["docker", "ps", "--format",
                           "{{.Names}}\t{{.Status}}"])
        containers = {}
        if rc == 0:
            for line in output.split("\n"):
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    containers[parts[0]] = parts[1]

        container_health = {
            "mysql": False, "redis": False, "namenode": False,
            "datanode1": False, "resourcemanager": False,
            "hive-server": False, "spark-master": False, "spark-worker": False,
            "zookeeper": False, "kafka": False,
        }
        missing = []
        for name, expected in container_health.items():
            status = containers.get(name, "")
            if "healthy" in status:
                container_health[name] = True
            elif "Up" in status:
                container_health[name] = True  # 启动中但不一定健康
            else:
                missing.append(name)

        self._record("infrastructure", "containers",
                      STATUS_OK if not missing else STATUS_UNAVAILABLE,
                      f"运行中: {sum(container_health.values())}/{len(container_health)} 缺失: {missing}" if missing else "全部就绪",
                      {"running": sum(container_health.values()),
                       "total": len(container_health),
                       "missing": missing})

        # 网络
        rc, _ = _run(["docker", "network", "inspect", "bigdata-net"])
        self._record("infrastructure", "network",
                      STATUS_OK if rc == 0 else STATUS_UNAVAILABLE,
                      "bigdata-net 可用" if rc == 0 else "bigdata-net 不存在")

        # 磁盘
        try:
            import shutil
            _, total, free = shutil.disk_usage(str(PROJECT_ROOT))
            self._record("infrastructure", "disk",
                          STATUS_OK if free > 5 * 1024**3 else STATUS_DEGRADED,
                          f"剩余: {free // 1024**3}GB / {total // 1024**3}GB",
                          {"free_gb": free // 1024**3, "total_gb": total // 1024**3})
        except Exception:
            pass

        self._update_layer_status("infrastructure")

    # ============================================================
    # 数据采集层检测
    # ============================================================

    def check_data_collector(self):
        """数据采集层 — 代码完整性、数据源可达性、存储层连通性"""
        # 1. 代码完整性
        expected_files = [
            "collectors/base_collector.py",
            "collectors/data_source_factory.py",
            "collectors/tencent_collector.py",
            "collectors/information_collector.py",
            "adapters/base_adapter.py",
            "adapters/collector_adapters.py",
            "pipeline/collection_pipeline.py",
            "pipeline/data_catalog.py",
            "storage/storage_manager.py",
            "config.py",
        ]
        missing_files = []
        for f in expected_files:
            if not (DATA_COLLECTOR_DIR / f).exists():
                missing_files.append(f)
        self._record("data_collector_layer", "code_integrity",
                      STATUS_OK if not missing_files else STATUS_UNAVAILABLE,
                      f"缺失 {len(missing_files)} 个文件: {missing_files}" if missing_files else f"{len(expected_files)} 个文件完整",
                      {"total": len(expected_files), "missing": len(missing_files)})

        # 2. Python 模块可导入
        sys.path.insert(0, str(DATA_COLLECTOR_DIR))
        modules = {
            "pandas": "", "requests": "",
        }
        import_errors = 0
        for mod, attr in modules.items():
            try:
                m = __import__(mod, fromlist=[attr])
                if attr and not hasattr(m, attr):
                    import_errors += 1
            except Exception:
                import_errors += 1
        # 尝试导入数据采集层内置模块（有依赖链，单独捕获）
        try:
            import collectors.base_collector
            import collectors.data_source_factory
            import adapters.base_adapter
            import storage.storage_manager
        except Exception:
            pass

        self._record("data_collector_layer", "python_modules",
                      STATUS_OK if import_errors == 0 else STATUS_DEGRADED,
                      f"{import_errors} 个模块导入失败" if import_errors else f"{len(modules)} 个模块可导入",
                      {"total": len(modules), "failed": import_errors})

        # 3. 数据源可达性（腾讯财经）
        rc, body = _http_get("https://qt.gtimg.cn/q=sh000001")
        tencent_ok = rc == 200 and len(body) > 10
        self._record("data_collector_layer", "tencent_api",
                      STATUS_OK if tencent_ok else STATUS_DEGRADED,
                      f"HTTP {rc}, 响应 {len(body)} 字节" if rc else f"不可达: {body[:50]}",
                      {"http_status": rc, "response_bytes": len(body)})

        # 4. 同花顺热点
        rc_hot, _ = _http_get("http://zx.10jqka.com.cn/event/api/getharden/")
        self._record("data_collector_layer", "ths_hot_api",
                      STATUS_OK if rc_hot in (200, 0) else STATUS_UNAVAILABLE,
                      f"HTTP {rc_hot}" if rc_hot else "超时或错误",
                      {"http_status": rc_hot if rc_hot else "timeout"})

        # 5. MySQL 连接（存储层）— 用 pymysql 实际连接，而非仅端口探测
        try:
            import pymysql
            test_conn = pymysql.connect(
                host="localhost", port=3306, user="root",
                password="hadoop123", database="stock_analysis",
                connect_timeout=3,
            )
            test_conn.close()
            mysql_ok = True
            mysql_detail = "pymysql 连接成功"
        except Exception as e:
            mysql_ok = False
            mysql_detail = f"连接失败: {str(e)[:80]}"
        self._record("data_collector_layer", "mysql_storage",
                      STATUS_OK if mysql_ok else STATUS_DEGRADED,
                      mysql_detail,
                      {"port": 3306, "reachable": mysql_ok})

        # 6. Redis 缓存
        redis_ok = _check_port("localhost", 6379)
        self._record("data_collector_layer", "redis_cache",
                      STATUS_OK if redis_ok else STATUS_DEGRADED,
                      "localhost:6379 可达" if redis_ok else "Redis 不可达（降级可用）",
                      {"port": 6379, "reachable": redis_ok})

        # 7. 数据目录
        data_dir = DATA_COLLECTOR_DIR / "data" / "raw"
        has_data = data_dir.is_dir() or data_dir.exists()
        csv_files = list(data_dir.glob("*.csv")) if data_dir.is_dir() else []
        json_files = list(data_dir.glob("*.json")) if data_dir.is_dir() else []
        self._record("data_collector_layer", "data_directory",
                      STATUS_OK,
                      f"CSV: {len(csv_files)}, JSON: {len(json_files)}",
                      {"csv_count": len(csv_files), "json_count": len(json_files)})

        self._update_layer_status("data_collector_layer")

    # ============================================================
    # 大数据处理层检测
    # ============================================================

    def check_bigdata_layer(self):
        """大数据处理层 — Hadoop/Hive/Spark/Kafka"""
        # 1. HDFS NameNode
        nn_ok = _check_port("localhost", 9870)
        rc, _ = _http_get("http://localhost:9870/")
        self._record("bigdata_layer", "hdfs_namenode",
                      STATUS_OK if nn_ok else STATUS_UNAVAILABLE,
                      f"WebUI HTTP {rc}" if rc else "不可达",
                      {"port": 9870, "http_status": rc})

        # 2. HDFS DataNode
        dn_ok = _check_port("localhost", 9864)
        self._record("bigdata_layer", "hdfs_datanode",
                      STATUS_OK if dn_ok else STATUS_UNAVAILABLE,
                      "localhost:9864 可达" if dn_ok else "不可达",
                      {"port": 9864})

        # 3. HDFS 文件系统（hdfs dfs -ls）
        rc, hdfs_output = _run(
            ["docker", "exec", "namenode", "hdfs", "dfs", "-ls", "/"],
            timeout=10,
        )
        hdfs_root_ok = rc == 0
        self._record("bigdata_layer", "hdfs_filesystem",
                      STATUS_OK if hdfs_root_ok else STATUS_UNAVAILABLE,
                      "HDFS 根目录可达" if hdfs_root_ok else f"不可达: {hdfs_output[:100]}",
                      {})

        # 4. YARN ResourceManager
        yarn_ok = _check_port("localhost", 8088)
        self._record("bigdata_layer", "yarn_resourcemanager",
                      STATUS_OK if yarn_ok else STATUS_UNAVAILABLE,
                      "localhost:8088 可达" if yarn_ok else "不可达",
                      {"port": 8088})

        # 5. Hive Server2
        hive_ok = _check_port("localhost", 10000)
        rc, _ = _run(
            ["docker", "exec", "hive-server",
             "/opt/hive/bin/beeline", "-u",
             "jdbc:hive2://localhost:10000",
             "-e", "SHOW DATABASES;"],
            timeout=15,
        )
        self._record("bigdata_layer", "hive_server",
                      STATUS_OK if rc == 0 else STATUS_UNAVAILABLE,
                      "Hive 查询正常" if rc == 0 else f"Hive 不可达: exit={rc}",
                      {"jdbc_port": 10000, "query_ok": rc == 0})

        # 6. Spark Master
        spark_ok = _check_port("localhost", 8080)
        self._record("bigdata_layer", "spark_master",
                      STATUS_OK if spark_ok else STATUS_UNAVAILABLE,
                      "localhost:8080 可达" if spark_ok else "不可达",
                      {"port": 8080, "webui": spark_ok})

        # 7. Spark Worker
        worker_ok = _check_port("localhost", 8081)
        self._record("bigdata_layer", "spark_worker",
                      STATUS_OK if worker_ok else STATUS_UNAVAILABLE,
                      "localhost:8081 可达" if worker_ok else "不可达",
                      {"port": 8081})

        # 8. Kafka
        kafka_ok = _check_port("localhost", 9092)
        if kafka_ok:
            rc, topics = _run(
                ["docker", "exec", "kafka",
                 "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"],
                timeout=10,
            )
            topic_list = topics.split("\n") if rc == 0 else []
        else:
            topic_list = []
        self._record("bigdata_layer", "kafka",
                      STATUS_OK if kafka_ok else STATUS_UNAVAILABLE,
                      f"Topic: {len(topic_list)}" if kafka_ok else "Kafka 未启动",
                      {"port": 9092, "topics": len(topic_list), "topic_list": topic_list})

        # 9. Spark Streaming 作业
        rc, apps = _run(
            ["docker", "exec", "spark-master",
             "/opt/spark/bin/spark-submit", "--version"],
            timeout=10,
        )
        self._record("bigdata_layer", "spark_streaming",
                      STATUS_DEGRADED if rc == 0 else STATUS_UNAVAILABLE,
                      "Spark 可用（无运行中 Streaming Job）" if rc == 0
                      else "Spark 不可用",
                      {"spark_available": rc == 0})

        # 10. 数据管道完整性（检查 HDFS 数据路径）
        rc, _ = _run(
            ["docker", "exec", "namenode",
             "hdfs", "dfs", "-ls", "/user/hadoop/stock_data/"],
            timeout=10,
        )
        self._record("bigdata_layer", "data_pipeline",
                      STATUS_DEGRADED if rc == 0 else STATUS_UNAVAILABLE,
                      "HDFS 数据路径存在" if rc == 0 else "无已处理数据",
                      {"has_data": rc == 0})

        self._update_layer_status("bigdata_layer")

    # ============================================================
    # 算法分析层检测
    # ============================================================

    def check_analysis_layer(self):
        """算法分析层 — 模型加载、计算耗时、推理耗时"""
        sys.path.insert(0, str(ANALYSIS_DIR))

        # 1. 代码完整性
        expected = [
            "utils/data_loader.py",
            "analysis_orchestrator.py",
            "technical/ma.py",
            "technical/macd.py",
            "technical/rsi.py",
            "technical/bollinger.py",
            "technical/kdj.py",
            "chanlun/fractal.py",
            "chanlun/analyzer.py",
            "quantitative/strategy_base.py",
            "quantitative/backtest.py",
        ]
        missing = [f for f in expected if not (ANALYSIS_DIR / f).exists()]
        self._record("analysis_layer", "code_integrity",
                      STATUS_OK if not missing else STATUS_UNAVAILABLE,
                      f"缺失: {missing}" if missing else f"{len(expected)} 个模块完整",
                      {"total": len(expected), "missing": len(missing)})

        # 2. 模块导入
        modules = [
            "technical", "technical.ma", "technical.macd",
            "technical.rsi", "technical.bollinger", "technical.kdj",
            "chanlun", "chanlun.fractal",
            "quantitative", "quantitative.strategy_base",
        ]
        import_errors = 0
        failed_modules = []
        for mod in modules:
            try:
                __import__(mod)
            except ImportError as e:
                import_errors += 1
                failed_modules.append(f"{mod}: {e}")

        self._record("analysis_layer", "module_import",
                      STATUS_OK if import_errors == 0 else STATUS_DEGRADED,
                      f"{import_errors} 个模块导入失败: {failed_modules}" if failed_modules else f"{len(modules)} 个模块可导入",
                      {"total": len(modules), "failed": import_errors})

        # 3. 数据加载延迟
        t0 = time.time()
        try:
            from utils.data_loader import load_kline
            df = load_kline("000001", days=60)
            load_ms = round((time.time() - t0) * 1000, 1)
            self._record("analysis_layer", "data_loading",
                          STATUS_OK if not df.empty else STATUS_DEGRADED,
                          f"延迟: {load_ms}ms, 行数: {len(df)}" if not df.empty else "无数据",
                          {"latency_ms": load_ms, "rows": len(df)})
        except Exception as e:
            self._record("analysis_layer", "data_loading",
                          STATUS_UNAVAILABLE, f"加载失败: {e}", {})

        # 4. 技术指标计算耗时
        t0 = time.time()
        try:
            import pandas as pd
            import numpy as np
            n = 500
            sample = pd.DataFrame({
                "date": pd.date_range(end=datetime.today(), periods=n, freq="B").strftime("%Y-%m-%d"),
                "open": np.random.randn(n).cumsum() + 10,
                "high": np.random.randn(n).cumsum() + 11,
                "low":  np.random.randn(n).cumsum() + 9,
                "close": np.random.randn(n).cumsum() + 10,
                "volume": np.random.randint(1e6, 1e8, n),
            })

            from technical.ma import MA
            from technical.macd import MACD
            from technical.rsi import RSI
            from technical.bollinger import BollingerBands
            from technical.kdj import KDJ

            ma_df = MA(sample)
            macd_df = MACD(sample)
            rsi_df = RSI(sample)
            boll_df = BollingerBands(sample)
            kdj_df = KDJ(sample)

            calc_ms = round((time.time() - t0) * 1000, 1)
            self._record("analysis_layer", "indicator_computation",
                          STATUS_OK if calc_ms < 1000 else STATUS_DEGRADED,
                          f"5指标计算: {calc_ms}ms/{n}行",
                          {"latency_ms": calc_ms, "samples": n,
                           "indicators": ["MA", "MACD", "RSI", "BOLL", "KDJ"]})
        except Exception as e:
            self._record("analysis_layer", "indicator_computation",
                          STATUS_UNAVAILABLE, f"计算失败: {e}", {})

        # 5. 缠论分析耗时
        t0 = time.time()
        try:
            from chanlun.fractal import merge_klines, find_fractals
            merged = merge_klines(sample)
            fractals = find_fractals(merged)
            chan_ms = round((time.time() - t0) * 1000, 1)
            self._record("analysis_layer", "chanlun_analysis",
                          STATUS_OK if len(fractals) > 0 else STATUS_DEGRADED,
                          f"缠论: {chan_ms}ms, {len(fractals)} 个分型",
                          {"latency_ms": chan_ms, "fractals": len(fractals)})
        except Exception as e:
            self._record("analysis_layer", "chanlun_analysis",
                          STATUS_UNAVAILABLE, f"缠论失败: {e}", {})

        # 6. 量化回测耗时
        t0 = time.time()
        try:
            from quantitative.strategy_base import StrategyEngine
            from quantitative.ma_strategy import MAStrategy
            engine = StrategyEngine()
            engine.add_strategy(MAStrategy())
            signals = engine.run_all(sample)
            quant_ms = round((time.time() - t0) * 1000, 1)
            self._record("analysis_layer", "quantitative_backtest",
                          STATUS_OK if signals else STATUS_DEGRADED,
                          f"策略回测: {quant_ms}ms, {len(signals)} 个信号",
                          {"latency_ms": quant_ms, "signals": len(signals)})
        except Exception as e:
            self._record("analysis_layer", "quantitative_backtest",
                          STATUS_DEGRADED, f"回测失败: {e}", {})

        # 7. 全量分析端到端耗时
        t0 = time.time()
        try:
            from analysis_orchestrator import analyze
            result = analyze("000001", days=120)
            e2e_ms = round((time.time() - t0) * 1000, 1)
            has_error = "error" in result
            self._record("analysis_layer", "end_to_end",
                          STATUS_OK if not has_error else STATUS_DEGRADED,
                          f"E2E: {e2e_ms}ms" if not has_error else f"部分失败: {result.get('error', '')}",
                          {"latency_ms": e2e_ms, "keys": list(result.keys())})
        except Exception as e:
            self._record("analysis_layer", "end_to_end",
                          STATUS_UNAVAILABLE, f"E2E 失败: {e}", {})

        self._update_layer_status("analysis_layer")

    # ============================================================
    # 报告生成
    # ============================================================

    def run(self) -> dict:
        """执行全量检查"""
        self.check_infrastructure()
        self.check_data_collector()
        self.check_bigdata_layer()
        self.check_analysis_layer()

        # 整体状态
        statuses = [
            self.results["data_collector_layer"]["status"],
            self.results["bigdata_layer"]["status"],
            self.results["analysis_layer"]["status"],
        ]
        if all(s == STATUS_OK for s in statuses):
            overall = STATUS_OK
        elif any(s == STATUS_UNAVAILABLE for s in statuses):
            overall = STATUS_UNAVAILABLE
        else:
            overall = STATUS_DEGRADED

        self.results["overall_status"] = overall
        self.results["summary"] = {
            "total_checks": self._total,
            "passed": self._total - self._failed,
            "failed": self._failed,
            "layers": {
                "infrastructure": self.results["infrastructure"]["status"],
                "data_collector": self.results["data_collector_layer"]["status"],
                "bigdata": self.results["bigdata_layer"]["status"],
                "analysis": self.results["analysis_layer"]["status"],
            }
        }
        return self.results

    def print_report(self, output_json: bool = False):
        """输出格式化报告"""
        r = self.results

        if output_json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
            return

        def icon(s):
            return {"available": "✅", "degraded": "⚠️", "unavailable": "❌"}.get(s, "❓")

        def layer_header(name, status):
            return f"{'='*55}\n{icon(status)} {name} [{status}] \n{'='*55}"

        print(f"\n{'#'*55}")
        print(f"#  系统健康检查报告")
        print(f"#  时间: {r['meta']['check_time']}")
        print(f"#  Python: {r['meta']['python_version']}")
        print(f"{'#'*55}")
        print(f"\n整体状态: {icon(r['overall_status'])} {r['overall_status']}")
        print(f"通过: {r['summary']['passed']}/{r['summary']['total_checks']}")

        for layer_name, layer_data in [
            ("🏗️  基础设施", "infrastructure"),
            ("📡 数据采集层", "data_collector_layer"),
            ("💾 大数据处理层", "bigdata_layer"),
            ("🧮 算法分析层", "analysis_layer"),
        ]:
            data = r[layer_data]
            print(f"\n{layer_header(layer_name, data['status'])}")
            for comp, info in data["components"].items():
                print(f"  {icon(info['status'])} {comp:30s} {info['detail'][:60]}")
                if info.get("metrics"):
                    m = info["metrics"]
                    parts = []
                    for k, v in m.items():
                        if isinstance(v, list):
                            parts.append(f"{k}={len(v)}")
                        elif isinstance(v, (int, float)):
                            parts.append(f"{k}={v}")
                        elif v:
                            parts.append(f"{k}={v}")
                    if parts:
                        print(f"    {' | '.join(parts)}")

        print(f"\n{'#'*55}")
        print(f"#  报告结束")
        print(f"{'#'*55}")


def watch_mode(interval: int = 30):
    """持续监控模式"""
    import datetime as dt
    print(f"🔄 持续监控启动 (每 {interval}s)")
    print(f"   按 Ctrl+C 停止\n")
    try:
        while True:
            now = dt.datetime.now().strftime("%H:%M:%S")
            hc = HealthCheck()
            r = hc.run()
            overall = r["overall_status"]
            icon_map = {"available": "✅", "degraded": "⚠️", "unavailable": "❌"}
            passed = r["summary"]["passed"]
            total = r["summary"]["total"]
            layers = r["summary"]["layers"]
            status_str = " | ".join(f"{k}={icon_map[v]}{v[:3]}" for k, v in layers.items())
            print(f"[{now}] {icon_map[overall]} {overall:12s} {passed}/{total} | {status_str}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n⏹️  监控停止")


def main():
    parser = argparse.ArgumentParser(description="系统健康检查")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--watch", type=int, default=0, help="持续监控间隔（秒）")
    parser.add_argument("--layer", choices=["collector", "bigdata", "analysis", "infra"],
                        help="指定层")

    args = parser.parse_args()

    if args.watch > 0:
        watch_mode(args.watch)
        return

    hc = HealthCheck()
    if args.layer == "infra":
        hc.check_infrastructure()
    elif args.layer == "collector":
        hc.check_data_collector()
    elif args.layer == "bigdata":
        hc.check_bigdata_layer()
    elif args.layer == "analysis":
        hc.check_analysis_layer()
    else:
        hc.run()

    hc.print_report(output_json=args.json)


if __name__ == "__main__":
    main()
