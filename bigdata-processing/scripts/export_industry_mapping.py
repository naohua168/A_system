#!/usr/bin/env python3
"""
行业映射 CSV 导出脚本
从 Hive (stock_basic) 或 MySQL (stock) 表导出 stock_code→industry 映射，
供 IndustryStatsMR MapReduce 作业通过 Hadoop DistributedCache 加载。

用法:
    # 从 Hive 导出（生产环境推荐）
    python export_industry_mapping.py --source hive --output hdfs

    # 从 MySQL 导出（开发/测试环境）
    python export_industry_mapping.py --source mysql --output local

    # 预览记录数
    python export_industry_mapping.py --source mysql --dry-run

生成的文件格式: CSV（无表头）
    stock_code,industry
"""
import argparse
import csv
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HDFS_BASE = "/user/hadoop/stock_data/basic"
HDFS_OUTPUT = f"{HDFS_BASE}/industry_mapping.csv"
LOCAL_OUTPUT = str(Path(__file__).resolve().parent.parent / "scripts" / "industry_mapping.csv")


def export_from_mysql(output_path: str, dry_run: bool = False) -> int:
    """从 MySQL stock 表导出行业映射"""
    try:
        import pymysql
    except ImportError:
        print("❌ 请安装 pymysql: pip install pymysql")
        return 0

    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "hadoop123")
    database = os.getenv("MYSQL_DB", "stock_analysis")

    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM stock WHERE industry IS NOT NULL AND industry != ''")
    total = cursor.fetchone()[0]
    print(f"📊 MySQL stock 表: {total} 条行业记录")

    if dry_run:
        cursor.close()
        conn.close()
        return total

    cursor.execute("""
        SELECT DISTINCT stock_code, industry
        FROM stock
        WHERE industry IS NOT NULL AND industry != ''
        ORDER BY stock_code
    """)

    count = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in cursor:
            writer.writerow([row[0].strip(), row[1].strip()])
            count += 1

    cursor.close()
    conn.close()
    print(f"✅ 已导出 {count} 条行业映射到 {output_path}")
    return count


def export_from_hive(output_path: str, hdfs_target: bool = False, dry_run: bool = False) -> int:
    """从 Hive stock_basic 表导出行业映射"""
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        print("❌ PySpark 不可用，请使用 --source mysql 从 MySQL 导出")
        return 0

    spark = SparkSession.builder \
        .appName("ExportIndustryMapping") \
        .master(os.getenv("SPARK_MASTER", "local[2]")) \
        .config("spark.sql.catalogImplementation", "hive") \
        .enableHiveSupport() \
        .getOrCreate()

    try:
        df = spark.sql("""
            SELECT DISTINCT code, industry
            FROM stock_analysis.stock_basic
            WHERE industry IS NOT NULL AND industry != ''
            ORDER BY code
        """)

        total = df.count()
        print(f"📊 Hive stock_basic 表: {total} 条行业记录")

        if dry_run:
            return total
        if dry_run:
            return total

        if hdfs_target:
            # 导出到 HDFS（不含分区）
            df.selectExpr("code", "industry") \
              .coalesce(1) \
              .write \
              .mode("overwrite") \
              .option("header", "false") \
              .option("delimiter", ",") \
              .csv(output_path)
            print(f"✅ 已导出到 HDFS: {output_path}/")
        else:
            # 导出到本地（单文件）
            local_df = df.coalesce(1)
            tmp_dir = tempfile.mkdtemp(prefix="industry_mapping_")
            local_df.write \
                .mode("overwrite") \
                .option("header", "false") \
                .option("delimiter", ",") \
                .csv(tmp_dir)

            # 合并单个 CSV
            import glob
            part_files = glob.glob(os.path.join(tmp_dir, "part-*.csv"))
            if part_files:
                import shutil
                shutil.copy(part_files[0], output_path)
                # 清理临时目录
                for f in glob.glob(os.path.join(tmp_dir, "*")):
                    os.remove(f)
                os.rmdir(tmp_dir)
                print(f"✅ 已导出 {total} 条行业映射到 {output_path}")

    finally:
        spark.stop()

    return total


def main():
    parser = argparse.ArgumentParser(description="行业映射 CSV 导出工具")
    parser.add_argument("--source", choices=["mysql", "hive"], default="mysql",
                        help="数据源: mysql (开发) 或 hive (生产)")
    parser.add_argument("--output", choices=["local", "hdfs"], default="local",
                        help="输出目标: local (本地文件) 或 hdfs (HDFS)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览记录数，不导出文件")
    parser.add_argument("--output-path", type=str, default=None,
                        help="自定义输出路径（默认自动选择）")
    args = parser.parse_args()

    # 确定输出路径
    if args.output_path:
        output_path = args.output_path
    elif args.output == "hdfs":
        output_path = HDFS_OUTPUT
    else:
        output_path = LOCAL_OUTPUT

    print(f"{'='*55}")
    print(f"📋 行业映射导出工具 [{datetime.now():%Y-%m-%d %H:%M:%S}]")
    print(f"{'='*55}")
    print(f"  数据源: {args.source}")
    print(f"  输出目: {'HDFS' if args.output == 'hdfs' else '本地'}")
    print(f"  输出路径: {output_path}")
    print(f"  DRY-RUN: {'是' if args.dry_run else '否'}")
    print()

    if args.source == "mysql":
        count = export_from_mysql(output_path, args.dry_run)
    else:
        count = export_from_hive(output_path, args.output == "hdfs", args.dry_run)

    if count == 0:
        print("⚠️  未找到行业数据，请确认数据采集已完成")
        sys.exit(1)

    print()
    print(f"✅ 完成！共 {count} 条行业映射")
    if args.source == "mysql":
        print()
        print("下一步:")
        print(f"  1. 上传到 HDFS: hdfs dfs -put {output_path} {HDFS_BASE}/")
        print(f"  2. 运行 MR 作业:")
        print(f"     hadoop jar ... IndustryStatsMR <input> <output>")
        print(f"     -files hdfs://{HDFS_BASE}/industry_mapping.csv")


if __name__ == "__main__":
    main()
