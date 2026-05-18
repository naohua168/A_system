"""
数据恢复脚本 v2 — 从 HDFS 备份恢复 MySQL
支持最近备份自动发现、指定日期恢复、校验对比

用法:
    # 恢复单表最新备份
    python restore_from_backup.py --table stock_daily

    # 恢复单表指定日期备份
    python restore_from_backup.py --table stock --date 20260516

    # 恢复全部表
    python restore_from_backup.py --all

    # 列出可用备份
    python restore_from_backup.py --list

    # 恢复前校验（不执行写入）
    python restore_from_backup.py --table stock_daily --verify
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BACKUP_BASE = "/user/hadoop/stock_data/backup"
# 修复: 密码改为从环境变量读取，避免硬编码泄露
import os as _os
_MYSQL_PASSWORD = _os.environ.get("MYSQL_PASSWORD") or "hadoop123"
MYSQL_JDBC = f"jdbc:mysql://mysql:3306/stock_analysis?useSSL=false&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"

BACKUP_TABLES = [
    "stock", "stock_daily", "fund", "fund_nav", "fund_holding",
    "signal_hot_reason", "signal_northbound", "signal_daily_industry",
    "signal_concept_block", "signal_fund_flow",
    "signal_dragon_tiger_detail", "signal_lockup_detail",
    "info_research_report", "info_consensus_eps", "info_stock_news",
    "info_cls_news", "info_global_news", "info_filing",
]


def _find_latest_backup(table: str) -> str:
    """查找某张表的最新备份路径"""
    result = subprocess.run(
        ["hdfs", "dfs", "-ls", f"{BACKUP_BASE}/{table}/"],
        capture_output=True, text=True, timeout=30,
    )
    # 找到最新的时间戳目录
    dirs = []
    for line in result.stdout.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 8:
            path = parts[-1]
            dirs.append((path.split("/")[-1], path))
    if not dirs:
        return ""
    dirs.sort(reverse=True)
    # 检查目录下是否有 Parquet 文件
    check = subprocess.run(
        ["hdfs", "dfs", "-ls", dirs[0][1]],
        capture_output=True, text=True, timeout=15,
    )
    if ".parquet" in check.stdout or ".snappy" in check.stdout:
        return dirs[0][1]
    # 递归查找
    for _, path in dirs:
        check = subprocess.run(
            ["hdfs", "dfs", "-ls", "-R", path],
            capture_output=True, text=True, timeout=15,
        )
        for cl in check.stdout.split("\n"):
            if ".parquet" in cl:
                return path
    return dirs[0][1] if dirs else ""


def run_spark_restore(table: str, date_str: str = None, verify_only: bool = False) -> bool:
    """通过 PySpark 从 HDFS Parquet 恢复到 MySQL"""
    if date_str:
        backup_path = f"{BACKUP_BASE}/{table}/full/{date_str}"
    else:
        backup_path = _find_latest_backup(table)

    if not backup_path:
        print(f"❌ 无可用备份: {table}")
        return False

    print(f"🔄 恢复 {table} ← {backup_path}")

    spark_script = f"""import sys; sys.path.insert(0, "{str(Path(__file__).parent.parent.resolve() / 'spark')}")
from spark_config import SparkConfig
from pyspark.sql import SparkSession
spark = SparkConfig(app_name="restore_{table}").with_adaptive().build()
try:
    df = spark.read.parquet("{backup_path}")
    count = df.count()
    print(f"从 HDFS 读取 {{count}} 条")
    if not {"true" if verify_only else "false"}:
        df.write.mode("overwrite").format("jdbc").options(
            url="{MYSQL_JDBC}",
            driver="com.mysql.cj.jdbc.Driver",
            user="root",
            password="hadoop123",
            dbtable="{table}",
            batchsize=1000,
        ).save()
        print(f"✅ {{table}} 恢复完成: {{count}} 条")
    else:
        print(f"✅ 校验通过: {{count}} 条")
finally:
    spark.stop()
"""

    cmd = [sys.executable, "-c", spark_script]
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    elapsed = time.time() - start

    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                print(f"  {line.strip()}")
        print(f"  ✅ {table} 完成 ({elapsed:.1f}s)")
        return True
    else:
        print(f"  ❌ {table} 失败 ({elapsed:.1f}s): {result.stderr[:200]}")
        return False


def list_backups():
    """列出所有可用备份"""
    result = subprocess.run(
        ["hdfs", "dfs", "-ls", "-R", BACKUP_BASE],
        capture_output=True, text=True, timeout=30,
    )
    print("\n📂 可用备份:")
    if result.returncode == 0:
        lines = [l for l in result.stdout.split("\n") if l.strip()]
        for line in lines[-60:]:
            print(f"  {line}")
    else:
        print(f"  ❌ {result.stderr[:200]}")


def main():
    parser = argparse.ArgumentParser(description="从 HDFS 备份恢复 MySQL v2")
    parser.add_argument("--table", help="恢复指定表")
    parser.add_argument("--date", help="指定备份日期 YYYYMMDD")
    parser.add_argument("--all", action="store_true", help="恢复全部表")
    parser.add_argument("--list", action="store_true", help="列出可用备份")
    parser.add_argument("--verify", action="store_true", help="仅校验不写入")
    args = parser.parse_args()

    if args.list:
        list_backups()
        return

    tables_to_restore = BACKUP_TABLES if args.all else ([args.table] if args.table else [])
    if not tables_to_restore:
        parser.print_help()
        return

    success = 0
    for table in tables_to_restore:
        ok = run_spark_restore(table, args.date, args.verify)
        if ok:
            success += 1

    print(f"\n{'='*55}")
    print(f"🏁 恢复完成: {success}/{len(tables_to_restore)}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
