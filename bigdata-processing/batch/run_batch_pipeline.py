"""
批处理管道调度器 v2 — 重构版
协调 Hive DML + Spark 批处理的 DAG 调度，支持依赖管理、并行执行、自动重试

用法:
    python run_batch_pipeline.py --mode daily
    python run_batch_pipeline.py --mode incremental --date 2026-05-13
    python run_batch_pipeline.py --mode rebuild
    python run_batch_pipeline.py --mode daily --dry-run    # 仅打印计划不执行
    python run_batch_pipeline.py --mode daily --skip-hive  # 跳过 Hive 步骤
    python run_batch_pipeline.py --mode daily --parallel   # 启用并行执行
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
LOG_DIR = PROJECT_ROOT.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 数据模型
# ============================================================
class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class StepResult:
    """单步执行结果"""
    name: str
    status: StepStatus
    elapsed: float = 0.0
    error: str = ""
    retries: int = 0
    depends_on: List[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return self.status in (StepStatus.SUCCESS, StepStatus.SKIPPED)


# ============================================================
# 配置文件管理
# ============================================================
def get_hive_dml_dir() -> Path:
    return PROJECT_ROOT / "hive" / "dml"


def get_spark_batch_dir() -> Path:
    return PROJECT_ROOT / "spark" / "batch"


def init_kafka_shell() -> str:
    return str(PROJECT_ROOT / "scripts" / "init_kafka_topics.sh")


# ============================================================
# DML 文件定义（有序列表）
# ============================================================
# 依赖关系: analysis_daily 是基础，其他依赖它
HIVE_DML_ORDER = [
    "analysis_daily.sql",           # 日均价统计（基础）
    "analysis_correlation.sql",     # 相关系数（依赖 daily）
    "analysis_change.sql",          # 涨跌幅统计（依赖 daily）
    "analysis_year_comparison.sql", # 年同比分析（依赖 daily）
    "analysis_technical.sql",       # 技术指标（依赖 daily）
    "analysis_signal_fusion.sql",   # 信号融合（依赖以上全部）
]

# Spark batch job 定义（有序列表）
SPARK_BATCH_JOBS = [
    "ma_trend.py",
    "trend_judge.py",
    "filter_stocks.py",
    "correlation.py",
    "sector_ranking.py",
    "monthly_return.py",
    "yearly_return.py",
]


# ============================================================
# 核心执行引擎
# ============================================================
class BatchPipeline:
    """批处理管道调度器 v2 — 支持 DAG 调度、重试、并行"""

    def __init__(self, mode: str = "daily", batch_date: str = None,
                 dry_run: bool = False, skip_hive: bool = False,
                 parallel: bool = False):
        self.mode = mode
        self.batch_date = batch_date or date.today().strftime("%Y-%m-%d")
        self.batch_id = f"{mode}_{self.batch_date}_{datetime.now():%H%M%S}"
        self.dry_run = dry_run
        self.skip_hive = skip_hive
        self.parallel = parallel
        self.results: List[StepResult] = []
        self._start_time = time.time()

        # 日志文件（批处理结束后写入摘要）
        self._log_file = LOG_DIR / f"pipeline_{self.batch_id}.log"

    # --------------------------------------------------
    # 执行方法
    # --------------------------------------------------

    def run(self):
        """执行完整批处理管道"""
        self._print_banner()
        self._add_file_handler()

        try:
            # Phase 0: 环境检查（可选）
            self._phase_check_env()

            # Phase 1: Hive DML 分析（串行，有依赖顺序）
            if not self.skip_hive:
                self._phase_hive_dml()
            else:
                logger.info("⏭️ Hive 步骤已跳过 (--skip-hive)")

            # Phase 2: Spark 批处理（可并行）
            self._phase_spark_batch()

            # Phase 3: 数据质量快照（新）
            if not self.dry_run:
                self._phase_quality_snapshot()

        except KeyboardInterrupt:
            logger.warning("⚠️ 管道被用户中断")
        except Exception as e:
            logger.error(f"❌ 管道异常终止: {e}", exc_info=True)
        finally:
            self._summary()

    # --------------------------------------------------
    # Phase 0: 环境检查
    # --------------------------------------------------

    def _phase_check_env(self):
        """检查 Hadoop/Hive 环境是否就绪"""
        if self.dry_run:
            logger.info("[DRY-RUN] 跳过环境检查")
            return

        logger.info("🔍 检查大数据环境...")

        # HDFS 检查
        ok = self._run_cmd(
            ["hdfs", "dfsadmin", "-report", "-summary"],
            "HDFS 状态", retries=1, timeout=15,
        )
        if not ok:
            logger.warning("⚠️ HDFS 不可用，部分功能可能受限")

        # Hive 检查
        if not self.skip_hive:
            ok = self._run_cmd(
                ["hive", "-e", "SELECT 1;"],
                "Hive 连接测试", retries=1, timeout=15,
            )
            if not ok:
                logger.warning("⚠️ Hive 不可用，将跳过 Hive DML 步骤")
                self.skip_hive = True

    # --------------------------------------------------
    # Phase 1: Hive DML
    # --------------------------------------------------

    def _phase_hive_dml(self):
        """执行 Hive DML 分析（串行，按依赖顺序）"""
        logger.info(f"{'='*55}")
        logger.info(f"📦 Phase 1: Hive DML 分析")
        logger.info(f"{'='*55}")

        # Step 0: MSCK REPAIR（分区修复）
        self._run_step("Hive MSCK REPAIR TABLE", [
            "hive", "-e",
            "USE stock_analysis; MSCK REPAIR TABLE stock_daily;"
        ], retries=2, timeout=120)

        # Step 1-N: DML 文件
        dml_dir = get_hive_dml_dir()
        for sql_file in HIVE_DML_ORDER:
            fp = dml_dir / sql_file
            if not fp.exists():
                logger.warning(f"  ⚠️ 文件不存在: {sql_file}")
                continue
            self._run_step(f"Hive DML {sql_file}", [
                "hive", "-f", str(fp)
            ], retries=1, timeout=300)

    # --------------------------------------------------
    # Phase 2: Spark 批处理
    # --------------------------------------------------

    def _phase_spark_batch(self):
        """执行 Spark 批处理（可选并行）"""
        logger.info(f"{'='*55}")
        logger.info(f"⚡ Phase 2: Spark 批处理")
        logger.info(f"   并行模式: {'ON' if self.parallel else 'OFF'}")
        logger.info(f"{'='*55}")

        batch_dir = get_spark_batch_dir()
        spark_submit = self._build_spark_submit()

        if self.parallel and len(SPARK_BATCH_JOBS) > 1:
            # 并行执行
            self._run_spark_parallel(batch_dir, spark_submit)
        else:
            # 串行执行
            for job in SPARK_BATCH_JOBS:
                fp = batch_dir / job
                if not fp.exists():
                    logger.warning(f"  ⚠️ 文件不存在: {job}")
                    continue
                self._run_step(f"Spark {job}", spark_submit + [str(fp)],
                               retries=1, timeout=600)
                if self.dry_run:
                    break

    def _build_spark_submit(self) -> list:
        """构建 spark-submit 命令（包含共享模块路径）"""
        spark_config_dir = str(PROJECT_ROOT / "spark")
        return [
            "spark-submit",
            "--master", os.getenv("SPARK_MASTER", "local[2]"),
            "--conf", "spark.sql.adaptive.enabled=true",
            "--conf", "spark.sql.catalogImplementation=hive",
            "--conf", f"spark.driver.extraClassPath={spark_config_dir}",
            "--py-files", f"{spark_config_dir}/spark_config.py",
        ]

    def _run_spark_parallel(self, batch_dir: Path, spark_submit: list):
        """并行执行多个 Spark Job"""
        jobs = [(job, spark_submit + [str(batch_dir / job)])
                for job in SPARK_BATCH_JOBS
                if (batch_dir / job).exists()]

        max_workers = min(len(jobs), 3)  # 最多并行3个
        logger.info(f"🚀 并行执行 {len(jobs)} 个 Spark Job (workers={max_workers})")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self._run_cmd, cmd, f"Spark {name}",
                                retries=1, timeout=600): name
                for name, cmd in jobs
            }
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    ok = future.result()
                    status = StepStatus.SUCCESS if ok else StepStatus.FAILED
                    self.results.append(StepResult(
                        name=f"Spark {name}",
                        status=status,
                    ))
                except Exception as e:
                    logger.error(f"❌ Spark {name} 并行执行异常: {e}")
                    self.results.append(StepResult(
                        name=f"Spark {name}",
                        status=StepStatus.FAILED,
                        error=str(e),
                    ))

    # --------------------------------------------------
    # Phase 3: 数据质量快照（新增）
    # --------------------------------------------------

    def _phase_quality_snapshot(self):
        """对处理结果做快速数据质量检查"""
        logger.info(f"{'='*55}")
        logger.info(f"✅ Phase 3: 数据质量检查 (QC)")
        logger.info(f"{'='*55}")

        try:
            from bigdata_quality import DataQualityChecker

            # 使用 hive 命令执行 Hive SQL 检查
            qc_tables = ["stock_daily", "stock_basic"]
            hive_available = self._check_command("hive")

            all_passed = True
            for table in qc_tables:
                if not hive_available:
                    logger.info(f"  - {table}: Hive 不可用，跳过")
                    continue

                result = subprocess.run(
                    ["hive", "-e",
                     f"USE stock_analysis; SELECT COUNT(*) FROM {table};"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    count = result.stdout.strip().split("\n")[-1].strip()
                    logger.info(f"  📊 {table}: {count} 行")
                    if count == "0":
                        logger.warning(f"  ⚠️ {table} 为空!")
                        all_passed = False
                else:
                    logger.warning(f"  ⚠️ 无法查询 {table}")
                    all_passed = False

            # 检查 HDFS 输出目录
            for job_name in ["ma_trend", "trend_judge", "filter_stocks"]:
                path = f"/user/hadoop/stock_data/analysis/spark/{job_name}"
                result = subprocess.run(
                    ["hdfs", "dfs", "-count", path],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    file_count = parts[0] if len(parts) > 0 else "?"
                    logger.info(f"  📁 {job_name}: {file_count} 文件")
                else:
                    logger.debug(f"  - {job_name}: 无输出")

            if not all_passed:
                logger.warning("  ⚠️ 部分数据质量检查未通过，请核实")

            # 生成 QC 报告 JSON
            report_path = LOG_DIR / f"qc_{self.batch_id}.json"
            import json as _json
            qc_summary = {
                "batch_id": self.batch_id,
                "mode": self.mode,
                "date": self.batch_date,
                "tables_checked": qc_tables,
                "all_passed": all_passed,
                "timestamp": datetime.now().isoformat(),
            }
            with open(report_path, "w", encoding="utf-8") as f:
                _json.dump(qc_summary, f, ensure_ascii=False, indent=2)
            logger.info(f"  📋 QC 报告: {report_path}")

        except ImportError:
            logger.warning("  ⚠️ bigdata_quality 模块未安装，跳过检查")
        except Exception as e:
            logger.warning(f"  ⚠️ 数据质量检查失败: {e}")

    # --------------------------------------------------
    # 核心命令执行
    # --------------------------------------------------

    def _run_step(self, name: str, command: list,
                  retries: int = 1, timeout: int = 300) -> bool:
        """带重试的步骤执行"""
        if self.dry_run:
            # 修复: f-string 缺少闭合括号，导致 dry-run 模式 SyntaxError
            logger.info(f"  [DRY-RUN] {' '.join(command[:4])}...")
            self.results.append(StepResult(name=name, status=StepStatus.SUCCESS))
            return True

        # 检查命令是否存在
        if not self._check_command(command[0]):
            logger.warning(f"  ⚠️ 命令 '{command[0]}' 未找到，跳过 {name}")
            self.results.append(StepResult(name=name, status=StepStatus.SKIPPED))
            return True

        last_error = ""
        for attempt in range(retries + 1):
            ok = self._run_cmd(command, name, attempt=attempt, timeout=timeout)
            if ok:
                return True
            last_error = f"重试 {retries} 次后仍失败"

            if attempt < retries:
                wait = min(2 ** attempt * 5, 60)  # 指数退避: 5s, 10s, 20s, ...
                logger.info(f"  等待 {wait}s 后重试 ({attempt+1}/{retries})...")
                time.sleep(wait)

        self.results.append(StepResult(
            name=name, status=StepStatus.FAILED, error=last_error,
            retries=retries,
        ))
        return False

    def _run_cmd(self, command: list, desc: str = "",
                 retries: int = 0, timeout: int = 60,
                 attempt: int = 0) -> bool:
        """执行单条命令"""
        label = f"{desc} (attempt {attempt+1})" if attempt > 0 else desc
        start = time.time()

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout
            )
            elapsed = time.time() - start

            if result.returncode == 0:
                logger.info(f"  ✅ {desc} ({elapsed:.1f}s)")
                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n")[-3:]:
                        logger.debug(f"     {line.strip()}")
                return True
            else:
                stderr = result.stderr[:300].strip()
                logger.warning(f"  ❌ {desc} 失败 (rc={result.returncode}, {elapsed:.1f}s)")
                if stderr:
                    logger.warning(f"     {stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"  ⏰ {desc} 超时 (>={timeout}s)")
            return False
        except FileNotFoundError:
            logger.warning(f"  ⚠️  {desc}: 命令未找到")
            return False
        except Exception as e:
            logger.error(f"  💥 {desc}: {e}")
            return False

    @staticmethod
    def _check_command(cmd: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run(
                ["which", cmd] if sys.platform != "win32" else ["where", cmd],
                capture_output=True, timeout=5,
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    # --------------------------------------------------
    # 辅助方法
    # --------------------------------------------------

    def _print_banner(self):
        """打印启动横幅"""
        logger.info(f"\n{'#'*55}")
        logger.info(f"# 📦 批处理管道 v2 [{self.batch_id}]")
        logger.info(f"# 模式: {self.mode.upper():10s} 日期: {self.batch_date}")
        logger.info(f"# 并行: {str(self.parallel):5s} Dry-Run: {str(self.dry_run):5s}")
        logger.info(f"{'#'*55}\n")

    def _add_file_handler(self):
        """添加文件日志处理器"""
        handler = logging.FileHandler(self._log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s"
        ))
        logger.addHandler(handler)

    def _summary(self):
        """输出执行摘要"""
        total_elapsed = time.time() - self._start_time

        # 统计结果
        success = sum(1 for r in self.results if r.status == StepStatus.SUCCESS)
        failed = sum(1 for r in self.results if r.status in (StepStatus.FAILED, StepStatus.TIMEOUT))
        skipped = sum(1 for r in self.results if r.status == StepStatus.SKIPPED)

        logger.info(f"\n{'='*55}")
        logger.info(f"🏁 批处理完成 [{self.batch_id}]")
        logger.info(f"   总耗时: {total_elapsed:.1f}s")
        logger.info(f"   成功: {success}  失败: {failed}  跳过: {skipped}  共: {len(self.results)} 步")
        logger.info(f"{'-'*55}")

        for r in self.results:
            icon = {
                StepStatus.SUCCESS: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.TIMEOUT: "⏰",
                StepStatus.RUNNING: "🔄",
                StepStatus.PENDING: "⏳",
            }.get(r.status, "❓")
            elapsed_str = f"({r.elapsed:.1f}s)" if r.elapsed else ""
            logger.info(f"  {icon} {r.name} {elapsed_str}")
            if r.error:
                logger.info(f"     └─ {r.error[:200]}")

        logger.info(f"{'='*55}\n")
        logger.info(f"📝 日志已保存: {self._log_file}")


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="批处理管道调度器 v2 — 重构版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python run_batch_pipeline.py --mode daily
    python run_batch_pipeline.py --mode incremental --date 2026-05-13
    python run_batch_pipeline.py --mode rebuild --parallel
    python run_batch_pipeline.py --mode daily --dry-run
    python run_batch_pipeline.py --mode daily --skip-hive
        """
    )
    parser.add_argument("--mode", choices=["daily", "incremental", "rebuild"],
                        default="daily", help="运行模式 (默认: daily)")
    parser.add_argument("--date", type=str, default=None,
                        help="处理日期 YYYY-MM-DD (默认: 今天)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅打印执行计划，不实际运行")
    parser.add_argument("--skip-hive", action="store_true",
                        help="跳过 Hive DML 步骤")
    parser.add_argument("--parallel", action="store_true",
                        help="并行执行 Spark Job (最多3个)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"],
                        default="INFO", help="日志级别")
    args = parser.parse_args()

    # 设置日志级别
    logger.setLevel(getattr(logging, args.log_level))

    pipeline = BatchPipeline(
        mode=args.mode,
        batch_date=args.date,
        dry_run=args.dry_run,
        skip_hive=args.skip_hive,
        parallel=args.parallel,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
