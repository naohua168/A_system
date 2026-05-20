#!/usr/bin/env python3
"""
Hive TEXTFILE → ORC 格式迁移脚本（增强版）

功能:
  - 自动创建 ORC 表（若不存在）
  - 支持检查点续传（避免中断后重头开始）
  - 详细的日志追踪（文件 + 控制台）
  - 迁移前/后数据量校验
  - 彩色进度显示

用法:
    # 查看迁移计划
    python migrate_hive_to_orc.py --dry-run

    # 执行全量迁移
    python migrate_hive_to_orc.py

    # 只迁移指定表
    python migrate_hive_to_orc.py --tables stock_daily

    # 从检查点恢复
    python migrate_hive_to_orc.py --resume

    # 迁移后切换表名
    python migrate_hive_to_orc.py --switch
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================
# 日志配置
# ============================================================
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"orc_migration_{datetime.now():%Y%m%d_%H%M%S}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("orc_migration")

# 检查点文件路径
CHECKPOINT_FILE = LOG_DIR / "orc_migration_checkpoint.json"

# ============================================================
# 迁移配置
# ============================================================
TABLES: Dict[str, dict] = {
    "stock_daily": {
        "orc_table": "stock_daily_orc",
        "columns": "stock_code, trade_date, open_price, high_price, low_price, "
                   "close_price, change_pct, volume, amount, amplitude, source",
        "partition_cols": "year, month",
        "partition_sql": "CAST(SUBSTR(trade_date, 1, 4) AS INT) AS year, "
                         "CAST(SUBSTR(trade_date, 6, 2) AS INT) AS month",
        "insert_sql": """
            INSERT OVERWRITE TABLE {orc_table} PARTITION (year, month)
            SELECT {columns},
                   {partition_sql}
            FROM {src_table}
        """,
        "create_sql": """
            CREATE TABLE IF NOT EXISTS {orc_table} (
                stock_code STRING COMMENT '股票代码',
                trade_date STRING COMMENT '交易日期',
                open_price DOUBLE COMMENT '开盘价',
                high_price DOUBLE COMMENT '最高价',
                low_price DOUBLE COMMENT '最低价',
                close_price DOUBLE COMMENT '收盘价',
                change_pct DOUBLE COMMENT '涨跌幅(%)',
                volume BIGINT COMMENT '成交量(股)',
                amount BIGINT COMMENT '成交额(元)',
                amplitude DOUBLE COMMENT '振幅(%)',
                source STRING COMMENT '数据来源'
            )
            COMMENT '日K线数据 ORC 格式优化表'
            PARTITIONED BY (year INT, month INT)
            STORED AS ORC
            TBLPROPERTIES (
                'orc.compress' = 'ZLIB',
                'orc.bloom.filter.columns' = 'stock_code',
                'orc.bloom.filter.fpp' = '0.05',
                'orc.row.index.stride' = '3000'
            )
        """,
    },
    "stock_basic": {
        "orc_table": "stock_basic_orc",
        "columns": "*",
        "insert_sql": "INSERT OVERWRITE TABLE {orc_table} SELECT * FROM {src_table}",
        "create_sql": """
            CREATE TABLE IF NOT EXISTS {orc_table} (
                code STRING COMMENT '股票代码',
                name STRING COMMENT '股票名称',
                market STRING COMMENT '所属市场',
                industry STRING COMMENT '所属行业',
                listing_date STRING COMMENT '上市日期',
                total_market_cap DOUBLE COMMENT '总市值',
                float_market_cap DOUBLE COMMENT '流通市值',
                pe DOUBLE COMMENT '市盈率',
                pb DOUBLE COMMENT '市净率',
                source STRING COMMENT '数据来源'
            )
            COMMENT '股票基本信息 ORC 格式优化表'
            STORED AS ORC
            TBLPROPERTIES (
                'orc.compress' = 'ZLIB'
            )
        """,
    },
}

USE_DB = "USE stock_analysis;"


# ============================================================
# 工具函数
# ============================================================

def save_checkpoint(table: str, step: str, row_count: Optional[int] = None):
    """保存迁移检查点"""
    checkpoint = {}
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            checkpoint = json.load(f)
    checkpoint[table] = {
        "step": step,
        "row_count": row_count,
        "timestamp": datetime.now().isoformat(),
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)
    logger.info("💾 检查点已保存: %s → %s", table, step)


def load_checkpoint() -> Dict[str, dict]:
    """加载检查点"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {}


def clear_checkpoint():
    """清除检查点"""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        logger.info("🗑️ 检查点已清除")


def run_hive(sql: str, timeout: int = 120, label: str = "") -> tuple[bool, str]:
    """执行 Hive SQL，返回 (成功, 输出摘要)"""
    display = sql[:100].replace("\n", " ")
    logger.info("▶ %s: %s...", label or "执行", display)

    start = time.time()
    try:
        result = subprocess.run(
            ["hive", "-e", sql],
            capture_output=True, text=True, timeout=timeout,
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            output = result.stdout.strip()[:200]
            logger.info("✅ %s 成功 (%.1fs)", label or "SQL", elapsed)
            return True, output
        else:
            err = result.stderr.strip()[:500]
            logger.error("❌ %s 失败 (%.1fs): %s", label or "SQL", elapsed, err)
            return False, err
    except subprocess.TimeoutExpired:
        logger.error("⏰ %s 超时 (>%ss)", label, timeout)
        return False, f"Timeout after {timeout}s"
    except FileNotFoundError:
        logger.error("⚠️ hive 命令未找到，请确认 Hive 已安装到 PATH")
        return False, "hive not found"


def get_table_row_count(table: str) -> Optional[int]:
    """获取 Hive 表行数"""
    success, output = run_hive(f"{USE_DB} SELECT COUNT(*) FROM {table};",
                               timeout=30, label=f"行数统计 {table}")
    if success:
        lines = [l.strip() for l in output.split("\n") if l.strip()]
        for line in reversed(lines):
            try:
                return int(line)
            except ValueError:
                continue
    return None


def ensure_orc_table_exists(table_config: dict, src_table: str) -> bool:
    """确保 ORC 目标表存在"""
    orc_table = table_config["orc_table"]
    create_sql = table_config["create_sql"].format(orc_table=orc_table)

    # 先检查表是否存在
    success, _ = run_hive(f"{USE_DB} DESCRIBE {orc_table};",
                          timeout=10, label=f"检查 {orc_table}")
    if success:
        logger.info("📋 ORC 表 %s 已存在，跳过创建", orc_table)
        return True

    logger.info("🏗️  创建 ORC 表 %s...", orc_table)
    ok, err = run_hive(f"{USE_DB} {create_sql}", timeout=60, label=f"创建 {orc_table}")
    if not ok:
        logger.error("❌ ORC 表 %s 创建失败: %s", orc_table, err)
    return ok


# ============================================================
# 迁移执行
# ============================================================

def migrate_table(src_table: str, table_config: dict,
                  dry_run: bool = False, resume: bool = False) -> bool:
    """迁移单张表"""
    orc_table = table_config["orc_table"]

    # 读取检查点
    checkpoint = {} if not resume else load_checkpoint()
    last_step = checkpoint.get(src_table, {}).get("step", "")

    logger.info("")
    logger.info("=" * 60)
    logger.info("📦 %s → %s", src_table, orc_table)
    logger.info("=" * 60)

    if dry_run:
        logger.info("  格式: TEXTFILE → ORC (ZLIB压缩 + Bloom Filter)")
        logger.info("  SQL: %s", table_config.get("insert_sql", "").format(
            orc_table=orc_table, src_table=src_table,
            columns=table_config.get("columns", "*"),
            partition_sql=table_config.get("partition_sql", ""),
        )[:150])
        return True

    # Step 1: 创建 ORC 表
    if last_step in ("", "create"):
        if not ensure_orc_table_exists(table_config, src_table):
            return False
        save_checkpoint(src_table, "create")
    else:
        logger.info("⏩ 跳过 Step 1 (创建): 检查点 %s", last_step)

    # Step 2: 检查源表数据量
    if last_step in ("", "create", "count"):
        logger.info("📊 统计源表 %s...", src_table)
        src_count = get_table_row_count(src_table)
        if src_count is None:
            logger.warning("⚠️ 无法获取源表行数，继续迁移")
        else:
            logger.info("📊 源表 %s 行数: %s", src_table, f"{src_count:,}")
        save_checkpoint(src_table, "count", src_count)
    else:
        src_count = checkpoint[src_table].get("row_count")
        logger.info("⏩ 跳过 Step 2 (统计): 上次行数 %s", src_count)

    # Step 3: 执行数据迁移
    if last_step in ("", "create", "count", "migrate"):
        logger.info("🔄 开始迁移数据 %s → %s...", src_table, orc_table)

        insert_sql = table_config["insert_sql"].format(
            orc_table=orc_table,
            src_table=src_table,
            columns=table_config.get("columns", "*"),
            partition_sql=table_config.get("partition_sql", ""),
        ).strip()
        # 移除多余空格/换行
        insert_sql = " ".join(insert_sql.split())

        ok, _ = run_hive(f"{USE_DB} {insert_sql}",
                         timeout=600, label=f"迁移 {src_table}")
        if not ok:
            logger.error("❌ %s 迁移失败", src_table)
            return False
        save_checkpoint(src_table, "migrate")
    else:
        logger.info("⏩ 跳过 Step 3 (迁移): 已完成")

    # Step 4: 校验目标表数据量
    logger.info("🔍 校验目标表 %s 数据量...", orc_table)
    orc_count = get_table_row_count(orc_table)
    if src_count is not None and orc_count is not None:
        if src_count == orc_count:
            logger.info("✅ 数据量校验通过: %s = %s (均为 %s)",
                        src_table, orc_table, f"{src_count:,}")
        else:
            logger.warning("⚠️ 数据量不一致: %s=%s, %s=%s",
                           src_table, f"{src_count:,}",
                           orc_table, f"{orc_count:,}")
    elif orc_count is not None:
        logger.info("📊 ORC 表 %s 行数: %s", orc_table, f"{orc_count:,}")

    # Step 5: 收集统计信息
    if last_step not in ("stats",):
        logger.info("📊 收集统计信息 %s...", orc_table)
        run_hive(f"{USE_DB} ANALYZE TABLE {orc_table} COMPUTE STATISTICS;",
                 timeout=120, label="ANALYZE")
        run_hive(f"{USE_DB} ANALYZE TABLE {orc_table} COMPUTE STATISTICS FOR COLUMNS;",
                 timeout=300, label="ANALYZE COLUMNS")
        save_checkpoint(src_table, "stats")
    else:
        logger.info("⏩ 跳过 Step 5 (统计信息): 已完成")

    logger.info("✅ %s 迁移完成", src_table)
    return True


def switch_tables(tables: Dict[str, dict], dry_run: bool = False):
    """迁移后切换表名 (TEXTFILE → ORC)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("🔄 切换表名 (TEXTFILE 备份 → ORC 正式)")
    logger.info("=" * 60)

    for src, cfg in tables.items():
        old_name = f"{src}_textfile_backup"

        if dry_run:
            logger.info("  [DRY-RUN] %s → %s", src, old_name)
            logger.info("  [DRY-RUN] %s → %s", cfg["orc_table"], src)
            continue

        # 备份源表
        ok, _ = run_hive(f"{USE_DB} ALTER TABLE {src} RENAME TO {old_name};",
                         timeout=30, label=f"备份 {src}")
        if not ok:
            logger.error("❌ %s 备份失败，跳过切换", src)
            continue

        # 切换 ORC 表为正式表
        ok, _ = run_hive(f"{USE_DB} ALTER TABLE {cfg['orc_table']} RENAME TO {src};",
                         timeout=30, label=f"切换 {cfg['orc_table']}")
        if not ok:
            logger.error("❌ %s 切换失败，请手动处理", cfg["orc_table"])
            # 尝试恢复
            run_hive(f"{USE_DB} ALTER TABLE {old_name} RENAME TO {src};",
                     timeout=30, label="恢复")
            continue

        logger.info("✅ %s(TEXTFILE) → %s", src, old_name)
        logger.info("✅ %s(ORC) → %s", cfg["orc_table"], src)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Hive TEXTFILE → ORC 格式迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="仅预览迁移计划")
    parser.add_argument("--tables", nargs="+", default=None,
                        help="指定迁移的表 (默认全部): stock_daily stock_basic")
    parser.add_argument("--switch", action="store_true",
                        help="迁移后切换表名 (TEXTFILE备份, ORC正式)")
    parser.add_argument("--resume", action="store_true",
                        help="从上次检查点恢复迁移")
    parser.add_argument("--clear-checkpoint", action="store_true",
                        help="清除检查点并从头开始")
    args = parser.parse_args()

    logger.info("")
    logger.info("#" * 60)
    logger.info("#  Hive ORC 迁移工具")
    logger.info("#  时间: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("#  日志: %s", LOG_FILE)
    logger.info("#" * 60)

    if args.clear_checkpoint:
        clear_checkpoint()
        if args.tables is None:
            return

    target_tables = {k: v for k, v in TABLES.items()
                     if args.tables is None or k in args.tables}

    if args.dry_run:
        logger.info("")
        logger.info("📋 迁移计划 (DRY-RUN)")
        for src, cfg in target_tables.items():
            logger.info("  • %s → %s", src, cfg["orc_table"])
            logger.info("    格式: TEXTFILE → ORC (ZLIB压缩 + Bloom Filter)")
            insert_sql = cfg["insert_sql"].format(
                orc_table=cfg["orc_table"], src_table=src,
                columns=cfg.get("columns", "*"),
                partition_sql=cfg.get("partition_sql", ""),
            )
            logger.info("    SQL: %s...", insert_sql[:120])
        logger.info("")
        logger.info("共 %d 张表", len(target_tables))
        return

    # 执行迁移
    all_ok = True
    for src, cfg in target_tables.items():
        ok = migrate_table(src, cfg, dry_run=False, resume=args.resume)
        if not ok:
            all_ok = False
            logger.error("❌ %s 迁移失败", src)

    # 表名切换
    if args.switch and all_ok:
        switch_tables(target_tables, dry_run=False)

    logger.info("")
    logger.info("=" * 60)
    if all_ok:
        logger.info("🎉 迁移完成！ 日志: %s", LOG_FILE)
    else:
        logger.warning("⚠️ 迁移部分完成，请检查日志: %s", LOG_FILE)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
