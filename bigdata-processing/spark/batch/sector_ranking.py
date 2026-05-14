"""
行业涨跌排行
JOIN stock_basic 计算各行业涨跌幅均值及周/月排名

用法:
    spark-submit \
        --master local[2] \
        --conf spark.sql.catalogImplementation=hive \
        sector_ranking.py

    支持批量回溯历史:
    spark-submit ... sector_ranking.py --days 5
"""

import argparse
from datetime import datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def create_spark_with_hive():
    """创建支持 Hive 的 Spark 会话"""
    return SparkSession.builder \
        .appName("SectorRanking") \
        .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
        .config("hive.metastore.uris", "thrift://hive-metastore:9083") \
        .config("spark.sql.catalogImplementation", "hive") \
        .enableHiveSupport() \
        .getOrCreate()


def compute_sector_daily_ranking(spark, trade_date=None):
    """计算指定日期各行业涨跌排行"""
    date_filter = f"AND d.trade_date = '{trade_date}'" if trade_date else ""

    df = spark.sql(f"""
        SELECT b.industry,
               COUNT(*) AS stock_count,
               ROUND(AVG(d.change_pct), 2) AS avg_change_pct,
               ROUND(SUM(d.change_pct), 2) AS total_change_pct,
               ROUND(MAX(d.change_pct), 2) AS max_change_pct,
               ROUND(MIN(d.change_pct), 2) AS min_change_pct,
               ROUND(SUM(CASE WHEN d.change_pct > 0 THEN 1 ELSE 0 END)
                     * 100.0 / COUNT(*), 1) AS up_ratio,
               ROUND(STDDEV(d.change_pct), 2) AS volatility
        FROM stock_analysis.stock_daily d
        JOIN stock_analysis.stock_basic b ON d.stock_code = b.code
        WHERE d.change_pct IS NOT NULL
          AND b.industry IS NOT NULL
          {date_filter}
        GROUP BY b.industry
        HAVING COUNT(*) >= 3
        ORDER BY avg_change_pct DESC
    """)

    date_str = trade_date or "最近交易日"
    print(f"\n{date_str} 行业涨跌排行:")
    df.show(50, truncate=False)
    return df


def compute_sector_weekly_period(spark, start_date, end_date):
    """计算一段时期内行业累计涨跌排行"""
    df = spark.sql(f"""
        SELECT b.industry,
               COUNT(DISTINCT d.stock_code) AS stock_count,
               ROUND(AVG(d.change_pct), 2) AS avg_daily_change,
               ROUND(SUM(d.change_pct), 2) AS cumulative_change_pct,
               ROUND(AVG(d.volume), 0) AS avg_volume,
               COUNT(DISTINCT d.trade_date) AS trade_days
        FROM stock_analysis.stock_daily d
        JOIN stock_analysis.stock_basic b ON d.stock_code = b.code
        WHERE d.trade_date BETWEEN '{start_date}' AND '{end_date}'
          AND d.change_pct IS NOT NULL
          AND b.industry IS NOT NULL
        GROUP BY b.industry
        HAVING COUNT(DISTINCT d.stock_code) >= 3
        ORDER BY cumulative_change_pct DESC
    """)

    print(f"\n{start_date} ~ {end_date} 行业累计涨跌排行:")
    df.show(50, truncate=False)
    return df


def save_results(df, label="latest"):
    """结果写入 HDFS Parquet"""
    output_path = f"/user/hadoop/stock_data/analysis/spark/sector_ranking/{label}/"
    df.write.mode("overwrite") \
        .option("compression", "snappy") \
        .parquet(output_path)
    print(f"已保存到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="行业涨跌排行")
    parser.add_argument("--trade-date", default=None, help="指定交易日，如 2026-05-08")
    parser.add_argument("--days", type=int, default=5,
                        help="回溯天数，用于计算累计排行，默认 5 天")
    args = parser.parse_args()

    spark = create_spark_with_hive()
    try:
        spark.sql("USE stock_analysis")
        print("开始计算行业排行...")

        # 1. 日排行
        daily_df = compute_sector_daily_ranking(spark, args.trade_date)
        save_results(daily_df, "daily")

        # 2. 周期累计排行
        end = args.trade_date or datetime.now().strftime("%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        start = (end_dt - timedelta(days=args.days)).strftime("%Y-%m-%d")
        period_df = compute_sector_weekly_period(spark, start, end)
        save_results(period_df, f"period_{args.days}d")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
