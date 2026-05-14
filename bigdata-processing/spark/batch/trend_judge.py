"""
趋势判断
使用 NTILE(2) 将数据分成前后两段，比较两段均值判断趋势方向（上涨/下跌/震荡）

用法:
    spark-submit \
        --master local[2] \
        --conf spark.sql.catalogImplementation=hive \
        trend_judge.py

    支持自定义窗口:
    spark-submit ... trend_judge.py --window 30 --min-records 15
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def create_spark_with_hive():
    """创建支持 Hive 的 Spark 会话"""
    return SparkSession.builder \
        .appName("TrendJudge") \
        .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
        .config("hive.metastore.uris", "thrift://hive-metastore:9083") \
        .config("spark.sql.catalogImplementation", "hive") \
        .enableHiveSupport() \
        .getOrCreate()


def judge_trend(spark, window_days=20, min_records=10):
    """
    对每只股票按时间排序后，用 NTILE(2) 分成前后两段，
    比较两段的均价：
    - 后段均价 > 前段均价 * 1.03 → UPTREND (上涨趋势)
    - 后段均价 < 前段均价 * 0.97 → DOWNTREND (下跌趋势)
    - 其余 → SIDEWAYS (震荡)
    """
    df = spark.sql(f"""
        WITH daily_sorted AS (
            SELECT stock_code, trade_date, close_price, volume
            FROM stock_analysis.stock_daily
            WHERE close_price IS NOT NULL
        ),
        recent_data AS (
            SELECT stock_code, trade_date, close_price, volume,
                   ROW_NUMBER() OVER (
                       PARTITION BY stock_code ORDER BY trade_date DESC
                   ) AS rn_desc
            FROM daily_sorted
        ),
        window_data AS (
            SELECT stock_code, trade_date, close_price, volume
            FROM recent_data
            WHERE rn_desc <= {window_days}
        ),
        ntile_data AS (
            SELECT stock_code, trade_date, close_price, volume,
                   NTILE(2) OVER (
                       PARTITION BY stock_code ORDER BY trade_date ASC
                   ) AS segment,
                   COUNT(*) OVER (PARTITION BY stock_code) AS total_records
            FROM window_data
        ),
        segment_stats AS (
            SELECT stock_code,
                   segment,
                   AVG(close_price) AS avg_price,
                   MAX(close_price) AS max_price,
                   MIN(close_price) AS min_price,
                   AVG(volume) AS avg_volume,
                   MAX(total_records) AS total_records
            FROM ntile_data
            GROUP BY stock_code, segment
        ),
        trend_calc AS (
            SELECT stock_code,
                   MAX(CASE WHEN segment = 1 THEN avg_price END) AS first_half_avg,
                   MAX(CASE WHEN segment = 2 THEN avg_price END) AS second_half_avg,
                   MAX(CASE WHEN segment = 1 THEN max_price END) AS first_half_high,
                   MAX(CASE WHEN segment = 2 THEN max_price END) AS second_half_high,
                   MAX(CASE WHEN segment = 1 THEN min_price END) AS first_half_low,
                   MAX(CASE WHEN segment = 2 THEN min_price END) AS second_half_low,
                   MAX(total_records) AS total_records,
                   (MAX(CASE WHEN segment = 2 THEN avg_price END)
                    - MAX(CASE WHEN segment = 1 THEN avg_price END))
                    / NULLIF(MAX(CASE WHEN segment = 1 THEN avg_price END), 0) * 100 AS change_pct
            FROM segment_stats
            GROUP BY stock_code
        )
        SELECT t.stock_code,
               b.name,
               b.industry,
               ROUND(t.first_half_avg, 2) AS first_half_avg,
               ROUND(t.second_half_avg, 2) AS second_half_avg,
               ROUND(t.change_pct, 2) AS change_pct,
               t.total_records,
               CASE
                   WHEN t.change_pct > 3 THEN 'UPTREND'
                   WHEN t.change_pct < -3 THEN 'DOWNTREND'
                   ELSE 'SIDEWAYS'
               END AS trend
        FROM trend_calc t
        LEFT JOIN stock_analysis.stock_basic b ON t.stock_code = b.code
        WHERE t.total_records >= {min_records}
        ORDER BY trend, ABS(t.change_pct) DESC
    """)

    print(f"\n趋势判断 (窗口={window_days}天, 最少记录={min_records}):")
    df.show(50, truncate=False)

    # 统计趋势分布
    df.createOrReplaceTempView("trend_results")
    spark.sql("""
        SELECT trend, COUNT(*) AS stock_count,
               ROUND(AVG(change_pct), 2) AS avg_change_pct
        FROM trend_results
        GROUP BY trend
        ORDER BY stock_count DESC
    """).show(truncate=False)

    return df


def save_results(df):
    """结果写入 HDFS Parquet"""
    output_path = "/user/hadoop/stock_data/analysis/spark/trend_judge/"
    df.write.mode("overwrite") \
        .option("compression", "snappy") \
        .parquet(output_path)
    print(f"已保存到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="趋势判断")
    parser.add_argument("--window", type=int, default=20,
                        help="分析窗口天数，默认 20")
    parser.add_argument("--min-records", type=int, default=10,
                        help="最少交易记录数，默认 10")
    args = parser.parse_args()

    spark = create_spark_with_hive()
    try:
        spark.sql("USE stock_analysis")
        print("开始判断趋势...")
        result_df = judge_trend(spark, args.window, args.min_records)
        print(f"共 {result_df.count()} 只股票")
        save_results(result_df)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
