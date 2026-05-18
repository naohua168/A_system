"""
月度收益率计算
使用 FIRST_VALUE / LAST_VALUE 窗口函数计算各月收益率

用法:
    spark-submit --master local[2] monthly_return.py
    spark-submit ... monthly_return.py --year 2026 --month 5
"""

import argparse
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# 修复: 使用 pathlib 代替 rsplit("/")，兼容 Windows 反斜杠路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spark_config import create_spark_session, save_dataframe, OUTPUT_PATHS


def compute_monthly_return(spark, year=None, month=None):
    """
    按 stock_code + year + month 分组，
    利用 FIRST_VALUE / LAST_VALUE 窗口函数取月内首末收盘价，
    计算月收益率 = (月末收盘价 - 月初收盘价) / 月初收盘价 * 100
    """
    conditions = []
    if year:
        conditions.append(f"year = {year}")
    if month:
        conditions.append(f"month = {month}")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    df = spark.sql(f"""
        WITH ranked AS (
            SELECT stock_code, year, month, trade_date, close_price,
                   ROW_NUMBER() OVER (
                       PARTITION BY stock_code, year, month ORDER BY trade_date ASC
                   ) AS rn_asc,
                   ROW_NUMBER() OVER (
                       PARTITION BY stock_code, year, month ORDER BY trade_date DESC
                   ) AS rn_desc
            FROM stock_analysis.stock_daily
            {where_clause}
        ),
        first_last AS (
            SELECT stock_code, year, month,
                   MAX(CASE WHEN rn_asc = 1 THEN close_price END) AS first_close,
                   MAX(CASE WHEN rn_desc = 1 THEN close_price END) AS last_close,
                   MAX(CASE WHEN rn_asc = 1 THEN trade_date END) AS first_date,
                   MAX(CASE WHEN rn_desc = 1 THEN trade_date END) AS last_date,
                   COUNT(*) AS trade_days
            FROM ranked
            GROUP BY stock_code, year, month
        )
        SELECT f.stock_code,
               b.name,
               f.year,
               f.month,
               f.first_date,
               f.last_date,
               ROUND(f.first_close, 2) AS first_close,
               ROUND(f.last_close, 2) AS last_close,
               ROUND((f.last_close - f.first_close) / f.first_close * 100, 2) AS monthly_return_pct,
               f.trade_days
        FROM first_last f
        LEFT JOIN stock_analysis.stock_basic b ON f.stock_code = b.code
        WHERE f.first_close IS NOT NULL AND f.first_close > 0
          AND f.trade_days >= 10
        ORDER BY f.year DESC, f.month DESC, monthly_return_pct DESC
    """)

    title = f"{year}年{month}月" if year and month else "全部月份"
    print(f"\n{title}收益率 Top30:")
    df.show(30, truncate=False)
    return df


def save_results(df, year=None, month=None):
    """结果写入 HDFS Parquet"""
    if year and month:
        path_suffix = f"year={year}/month={month}"
    elif year:
        path_suffix = f"year={year}"
    else:
        path_suffix = "all"
    output_path = f"{OUTPUT_PATHS['monthly_return']}/{path_suffix}"
    save_dataframe(df, output_path)


def main():
    parser = argparse.ArgumentParser(description="月度收益率计算")
    parser.add_argument("--year", type=int, default=None, help="指定年份，如 2026")
    parser.add_argument("--month", type=int, default=None, help="指定月份，如 5")
    args = parser.parse_args()

    spark = create_spark_session("MonthlyReturn")
    try:
        spark.sql("USE stock_analysis")
        print("开始计算月收益率...")
        result_df = compute_monthly_return(spark, args.year, args.month)
        print(f"共 {result_df.count()} 条记录")
        save_results(result_df, args.year, args.month)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
