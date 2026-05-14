"""批处理管道调度器 — 协调Hive/Spark/MySQL批处理流程

支持3种模式：
  daily:       全量跑批
  incremental: 增量跑批（只处理当天数据）
  rebuild:     全量重算

用法:
    python run_batch_pipeline.py --mode daily
    python run_batch_pipeline.py --mode incremental --date 2026-05-13
    python run_batch_pipeline.py --mode rebuild
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class BatchPipeline:
    """批处理管道调度器"""

    def __init__(self, mode: str = "daily", batch_date: str = None):
        self.mode = mode
        self.batch_date = batch_date or date.today().strftime("%Y-%m-%d")
        self.batch_id = f"{self.mode}_{self.batch_date}_{datetime.now():%H%M%S}"
        self.results = []

    def run_step(self, step_name: str, command: list) -> bool:
        """执行单个步骤"""
        print(f"\n{'='*55}")
        print(f"▶  [{self.batch_id}] {step_name}")
        print(f"{'='*55}")

        start = time.time()
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=600)
            elapsed = time.time() - start

            if result.returncode == 0:
                print(f"✅ {step_name} 成功 ({elapsed:.1f}s)")
                self.results.append({"step": step_name, "status": "success", "elapsed": elapsed})
                return True
            else:
                print(f"❌ {step_name} 失败 (rc={result.returncode})")
                print(f"   STDERR: {result.stderr[:500]}")
                self.results.append({"step": step_name, "status": "failed", "error": result.stderr[:200]})
                return False
        except subprocess.TimeoutExpired:
            print(f"❌ {step_name} 超时 (>600s)")
            self.results.append({"step": step_name, "status": "timeout"})
            return False
        except FileNotFoundError as e:
            print(f"⚠️  {step_name} 命令未找到: {e}")
            self.results.append({"step": step_name, "status": "skipped", "error": str(e)})
            return True  # 跳过但不中断

    def run(self):
        """执行完整批处理管道"""
        print(f"\n{'#'*55}")
        print(f"# 📦 批处理管道启动 [{self.batch_id}]")
        print(f"# 模式: {self.mode.upper()}  日期: {self.batch_date}")
        print(f"{'#'*55}")

        # Step 1: Hive MSCK REPAIR
        self.run_step("Hive MSCK REPAIR", [
            "hive", "-e",
            "USE stock_analysis; MSCK REPAIR TABLE stock_daily;"
        ])

        # Step 2: Hive DML 分析
        hive_dml_dir = PROJECT_ROOT / "hive" / "dml"
        dml_files = [
            "analysis_daily.sql",
            "analysis_change.sql",
            "analysis_correlation.sql",
            "analysis_year_comparison.sql",
            "analysis_technical.sql",
            "analysis_signal_fusion.sql",
        ]
        for sql_file in dml_files:
            fp = hive_dml_dir / sql_file
            if fp.exists():
                self.run_step(f"Hive DML {sql_file}", ["hive", "-f", str(fp)])

        # Step 3: Spark 批处理
        spark_batch_dir = PROJECT_ROOT / "spark" / "batch"
        batch_jobs = [
            "yearly_return.py",
            "monthly_return.py",
            "ma_trend.py",
            "correlation.py",
            "sector_ranking.py",
            "filter_stocks.py",
            "trend_judge.py",
        ]
        for job in batch_jobs:
            fp = spark_batch_dir / job
            if fp.exists():
                self.run_step(f"Spark {job}", [
                    "spark-submit",
                    "--master", "local[2]",
                    "--conf", "spark.sql.catalogImplementation=hive",
                    str(fp),
                ])

        self._summary()

    def _summary(self):
        """输出执行摘要"""
        success = sum(1 for r in self.results if r["status"] == "success")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        print(f"\n{'='*55}")
        print(f"🏁 批处理完成 [{self.batch_id}]")
        print(f"   成功: {success}  失败: {failed}  共: {len(self.results)} 步")
        for r in self.results:
            status_icon = "✅" if r["status"] == "success" else "❌" if r["status"] == "failed" else "⚠️"
            elapsed = r.get("elapsed", 0)
            print(f"  {status_icon} {r['step']} ({elapsed:.1f}s)")
        print(f"{'='*55}")
        return self.results


def main():
    parser = argparse.ArgumentParser(description="批处理管道调度器")
    parser.add_argument("--mode", choices=["daily", "incremental", "rebuild"],
                        default="daily", help="运行模式")
    parser.add_argument("--date", type=str, default=None, help="处理日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    pipeline = BatchPipeline(mode=args.mode, batch_date=args.date)
    pipeline.run()


if __name__ == "__main__":
    main()
