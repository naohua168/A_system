"""
年度收益率计算
使用 ROW_NUMBER 窗口函数取每年首末行，计算年收益率

用法:
    spark-submit \
        --master local[2] \
        --conf spark.sql.catalogImplementation=hive \
        yearly_return.py

    支持指定年份:
    spark-submit ... yearly_return.py --year 2025
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def create_spark_with_hive():
    """创建支持 Hive 的 Spark 会话"""
    return SparkSession.builder \
        .appName("YearlyReturn") \
        .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
        .config("hive.metastore.uris", "thrift://hive-metastore:9083") \
        .config("spark.sql.catalogImplementation", "hive") \
        .enableHiveSupport() \
        .getOrCreate()


def compute_yearly_return(spark, year=None):
    """
    利用 ROW_NUMBER 窗口函数取出每年首个交易日和末个交易日，
    计算年收益率 = (年末收盘价 - 年初收盘价) / 年初收盘价 * 100
    """
    condition = ""
    if year:
        condition = f"WHERE year = {year}"

    df = spark.sql(f"""
        WITH ranked AS (
            SELECT stock_code, year, trade_date, close_price,
                   ROW_NUMBER() OVER (
                       PARTITION BY stock_code, year ORDER BY trade_date ASC
                   ) AS rn_asc,
                   ROW_NUMBER() OVER (
                       PARTITION BY stock_code, year ORDER BY trade_date DESC
                   ) AS rn_desc
            FROM stock_analysis.stock_daily
            {condition}
        ),
        first_last AS (
            SELECT stock_code, year,
                   MAX(CASE WHEN rn_asc = 1 THEN close_price END) AS first_close,
                   MAX(CASE WHEN rn_desc = 1 THEN close_price END) AS last_close,
                   MAX(CASE WHEN rn_asc = 1 THEN trade_date END) AS first_date,
                   MAX(CASE WHEN rn_desc = 1 THEN trade_date END) AS last_date
            FROM ranked
            GROUP BY stock_code, year
        )
        SELECT f.stock_code,
               b.name,
               f.year,
               f.first_date,
               f.last_close,
               f.last_date,
               f.first_close,
               ROUND((f.last_close - f.first_close) / f.first_close * 100, 2) AS yearly_return_pct,
               ROUND(f.last_close, 2) AS last_close
        FROM first_last f
        LEFT JOIN stock_analysis.stock_basic b ON f.stock_code = b.code
        WHERE f.first_close IS NOT NULL AND f.first_close > 0
        ORDER BY f.year DESC, yearly_return_pct DESC
    """)

    title = f"{year} 年度" if year else "全部"
    print(f"\n{title}收益率 Top50:")
    df.show(50, truncate=False)
    return df


def save_results(df, year=None):
    """结果写入 HDFS Parquet"""
    path_suffix = f"yearly_return/year={year}" if year else "yearly_return/all"
    output_path = f"/user/hadoop/stock_data/analysis/spark/{path_suffix}"
    df.write.mode("overwrite") \
        .option("compression", "snappy") \
        .parquet(output_path)
    print(f"已保存到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="年度收益率计算")
    parser.add_argument("--year", type=int, default=None, help="指定年份，如 2025")
    args = parser.parse_args()

    spark = create_spark_with_hive()
    try:
        spark.sql("USE stock_analysis")
        print("开始计算年收益率...")
        result_df = compute_yearly_return(spark, args.year)
        print(f"共 {result_df.count()} 条记录")
        save_results(result_df, args.year)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
