"""
Spark SQL 查询 Hive 数据仓库
直接从 Hive 表读取数据进行分析，结果写回 HDFS/MySQL

用法:
    spark-submit --master local[2] hive_query.py

    或在 PySpark shell 中:
    spark.sql("USE stock_analysis").show()
    spark.sql("SELECT * FROM stock_daily LIMIT 10").show()
"""

import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# 修复: 使用 pathlib 代替 rsplit("/")，兼容 Windows 反斜杠路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spark_config import create_spark_session, save_dataframe, OUTPUT_PATHS


def query_top_gainers(spark, trade_date="2026-05-08", top_n=20):
    """查询指定日期的涨幅榜"""
    df = spark.sql(f"""
        SELECT d.stock_code, b.name, d.close_price, d.change_pct, d.volume
        FROM stock_analysis.stock_daily d
        JOIN stock_analysis.stock_basic b ON d.stock_code = b.code
        WHERE d.trade_date = '{trade_date}'
          AND d.change_pct IS NOT NULL
        ORDER BY d.change_pct DESC
        LIMIT {top_n}
    """)
    print(f"\n📈 {trade_date} 涨幅榜 Top{top_n}:")
    df.show(truncate=False)
    return df


def query_sector_performance(spark, trade_date="2026-05-08"):
    """查询行业涨跌排行"""
    df = spark.sql(f"""
        SELECT b.industry,
               COUNT(*) AS stock_count,
               ROUND(AVG(d.change_pct), 2) AS avg_change_pct,
               ROUND(SUM(CASE WHEN d.change_pct > 0 THEN 1 ELSE 0 END)
                     * 100.0 / COUNT(*), 1) AS up_ratio
        FROM stock_analysis.stock_daily d
        JOIN stock_analysis.stock_basic b ON d.stock_code = b.code
        WHERE d.trade_date = '{trade_date}'
          AND b.industry IS NOT NULL
        GROUP BY b.industry
        ORDER BY avg_change_pct DESC
    """)
    print(f"\n🏢 {trade_date} 行业涨跌排行:")
    df.show(truncate=False)
    return df


def query_monthly_summary(spark, year=2026, month=5):
    """月度汇总统计"""
    df = spark.sql(f"""
        SELECT stock_code,
               ROUND(AVG(close_price), 2) AS avg_price,
               ROUND(MIN(low_price), 2) AS min_price,
               ROUND(MAX(high_price), 2) AS max_price,
               ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS return_pct,
               ROUND(SUM(volume), 0) AS total_volume,
               COUNT(*) AS trade_days
        FROM stock_analysis.stock_daily
        WHERE year = {year} AND month = {month}
        GROUP BY stock_code
        HAVING COUNT(*) >= 10
        ORDER BY return_pct DESC
        LIMIT 20
    """)
    print(f"\n📊 {year}年{month}月 回报率 Top20:")
    df.show(truncate=False)
    return df


def main():
    spark = create_spark_session("StockHiveQuery")

    try:
        print("🔍 查询 Hive 数据仓库 (stock_analysis)")

        # 1. 查看可用表
        spark.sql("SHOW DATABASES").show()
        spark.sql("USE stock_analysis")
        spark.sql("SHOW TABLES").show()

        # 2. 执行分析查询
        query_top_gainers(spark)
        query_sector_performance(spark)
        query_monthly_summary(spark)

        # 3. 结果写入 HDFS Parquet
        df = query_top_gainers(spark, top_n=100)
        save_dataframe(df, OUTPUT_PATHS["top_gainers"])

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
