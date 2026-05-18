#!/usr/bin/env python3
"""
Hive TEXTFILE → ORC 格式迁移脚本
将已有的 TEXTFILE 格式 Hive 表迁移到 ORC 格式，提升查询性能 5~15 倍

用法:
    # 查看迁移计划
    python migrate_hive_to_orc.py --dry-run

    # 执行全量迁移
    python migrate_hive_to_orc.py

    # 只迁移指定表
    python migrate_hive_to_orc.py --tables stock_daily

    # 迁移后切换表名
    python migrate_hive_to_orc.py --switch
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime

# ============================================================
# 迁移配置
# ============================================================
TABLES = {
    "stock_daily": {
        "orc_table": "stock_daily_orc",
        "columns": "stock_code, trade_date, open_price, high_price, low_price, "
                   "close_price, change_pct, volume, amount, amplitude, source",
        "partition_cols": "year, month",
        "partition_sql": "CAST(SUBSTR(trade_date, 1, 4) AS INT) AS year, "
                         "CAST(SUBSTR(trade_date, 6, 2) AS INT) AS month",
        "insert_sql": """
            INSERT OVERWRITE TABLE stock_daily_orc PARTITION (year, month)
            SELECT {columns},
                   {partition_sql}
            FROM stock_daily
        """,
    },
    "stock_basic": {
        "orc_table": "stock_basic_orc",
        "columns": "*",
        "insert_sql": "INSERT OVERWRITE TABLE stock_basic_orc SELECT * FROM stock_basic",
    },
}


def run_hive(sql: str, timeout: int = 120) -> bool:
    """执行 Hive SQL"""
    print(f"  ▶ {sql[:80]}...")
    start = time.time()
    try:
        result = subprocess.run(
            ["hive", "-e", sql],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            print(f"  ✅ 成功 ({elapsed:.1f}s)")
            return True
        else:
            print(f"  ❌ 失败 ({elapsed:.1f}s): {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ⏰ 超时 (>={timeout}s)")
        return False
    except FileNotFoundError:
        print(f"  ⚠️ hive 命令未找到")
        return False


def run_migration(dry_run: bool = False, tables: list = None, switch: bool = False):
    """执行 Hive 表迁移"""
    target_tables = {k: v for k, v in TABLES.items()
                     if tables is None or k in tables}

    if dry_run:
        print(f"\n{'='*55}")
        print(f"📋 迁移计划 (DRY-RUN)")
        print(f"{'='*55}")
        for src, cfg in target_tables.items():
            print(f"\n  {src} → {cfg['orc_table']}")
            print(f"  格式: TEXTFILE → ORC (ZLIB压缩 + Bloom Filter)")
            print(f"  SQL: {cfg['insert_sql'][:100]}...")
        print(f"\n共 {len(target_tables)} 张表")
        return

    print(f"\n{'='*55}")
    print(f"🔄 Hive 表 ORC 迁移 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
    print(f"{'='*55}")

    use_db = "USE stock_analysis;"

    for src, cfg in target_tables.items():
        print(f"\n{'─'*50}")
        print(f"📦 {src} → {cfg['orc_table']}")
        print(f"{'─'*50}")

        # Step 1: 检查 ORC 表是否存在
        if not run_hive(f"{use_db} DESCRIBE {cfg['orc_table']};", timeout=10):
            print(f"  ⚠️ ORC 表 {cfg['orc_table']} 不存在，请先运行 stock_daily_orc.sql")
            continue

        # Step 2: 检查源表数据量
        src_result = subprocess.run(
            ["hive", "-e", f"{use_db} SELECT COUNT(*) FROM {src};"],
            capture_output=True, text=True, timeout=30,
        )
        src_count = src_result.stdout.strip().split("\n")[-1].strip() if src_result.returncode == 0 else "?"
        print(f"  📊 源表 {src} 行数: {src_count}")

        # Step 3: 执行数据迁移
        insert_sql = cfg["insert_sql"].format(
            columns=cfg.get("columns", "*"),
            partition_sql=cfg.get("partition_sql", ""),
        )
        ok = run_hive(f"{use_db} {insert_sql}", timeout=600)
        if not ok:
            print(f"  ⚠️ {src} 迁移失败，跳过")
            continue

        # Step 4: 收集统计信息
        print("  📊 收集统计信息...")
        run_hive(f"{use_db} ANALYZE TABLE {cfg['orc_table']} COMPUTE STATISTICS;", timeout=120)
        run_hive(f"{use_db} ANALYZE TABLE {cfg['orc_table']} COMPUTE STATISTICS FOR COLUMNS;",
                 timeout=300)

    # 表名切换
    if switch and not dry_run:
        print(f"\n{'─'*50}")
        print(f"🔄 切换表名 (TEXTFILE → ORC)")
        print(f"{'─'*50}")
        for src, cfg in target_tables.items():
            old_name = f"{src}_textfile_backup"
            run_hive(f"{use_db} ALTER TABLE {src} RENAME TO {old_name};", timeout=30)
            run_hive(f"{use_db} ALTER TABLE {cfg['orc_table']} RENAME TO {src};", timeout=30)
            print(f"  ✅ {src}(TEXTFILE) → {old_name}")
            print(f"  ✅ {cfg['orc_table']}(ORC) → {src}")

    print(f"\n{'='*55}")
    print(f"✅ 迁移完成")
    print(f"{'='*55}")


def main():
    parser = argparse.ArgumentParser(description="Hive TEXTFILE → ORC 迁移")
    parser.add_argument("--dry-run", action="store_true", help="仅预览迁移计划")
    parser.add_argument("--tables", nargs="+", default=None,
                        help="指定迁移的表 (默认全部): stock_daily stock_basic")
    parser.add_argument("--switch", action="store_true",
                        help="迁移后切换表名 (TEXTFILE备份, ORC正式)")
    args = parser.parse_args()

    run_migration(args.dry_run, args.tables, args.switch)


if __name__ == "__main__":
    main()
