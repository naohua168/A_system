"""
均线趋势分析
使用 AVG() OVER 滑动窗口计算 MA5/10/20/60，判断金叉/死叉

用法:
    spark-submit --master local[2] ma_trend.py
    spark-submit ... ma_trend.py --start-date 2026-01-01 --end-date 2026-05-08
"""

import argparse
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# 修复: 使用 pathlib 代替 rsplit("/")，兼容 Windows 反斜杠路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spark_config import create_spark_session, save_dataframe, count_and_show, OUTPUT_PATHS


def compute_ma_trend(spark, start_date=None, end_date=None):
    """
    对每只股票按时间排序后：
    1. 计算 MA5 / MA10 / MA20 / MA60 移动均线
    2. 判断金叉（MA5 上穿 MA10）和死叉（MA5 下穿 MA10）
    """
    conditions = []
    if start_date:
        conditions.append(f"trade_date >= '{start_date}'")
    if end_date:
        conditions.append(f"trade_date <= '{end_date}'")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    df = spark.sql(f"""
        WITH ma_calc AS (
            SELECT stock_code, trade_date, close_price, volume,
                   AVG(close_price) OVER (
                       PARTITION BY stock_code ORDER BY trade_date
                       ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                   ) AS ma5,
                   AVG(close_price) OVER (
                       PARTITION BY stock_code ORDER BY trade_date
                       ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                   ) AS ma10,
                   AVG(close_price) OVER (
                       PARTITION BY stock_code ORDER BY trade_date
                       ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                   ) AS ma20,
                   AVG(close_price) OVER (
                       PARTITION BY stock_code ORDER BY trade_date
                       ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                   ) AS ma60
            FROM stock_analysis.stock_daily
            {where_clause}
        ),
        signals AS (
            SELECT stock_code, trade_date, close_price, volume,
                   ROUND(ma5, 2) AS ma5,
                   ROUND(ma10, 2) AS ma10,
                   ROUND(ma20, 2) AS ma20,
                   ROUND(ma60, 2) AS ma60,
                   CASE
                       WHEN ma5 > ma10 AND LAG(ma5) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) <= LAG(ma10) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) THEN 'GOLDEN_CROSS'
                       WHEN ma5 < ma10 AND LAG(ma5) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) >= LAG(ma10) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) THEN 'DEATH_CROSS'
                       ELSE 'NORMAL'
                   END AS cross_signal
            FROM ma_calc
            WHERE ma5 IS NOT NULL AND ma10 IS NOT NULL
        )
        SELECT s.stock_code, b.name, s.trade_date, s.close_price,
               s.ma5, s.ma10, s.ma20, s.ma60, s.volume,
               s.cross_signal
        FROM signals s
        LEFT JOIN stock_analysis.stock_basic b ON s.stock_code = b.code
        WHERE s.cross_signal IN ('GOLDEN_CROSS', 'DEATH_CROSS')
        ORDER BY s.trade_date DESC, s.stock_code
    """)

    print("\n均线金叉/死叉信号:")
    df.show(50, truncate=False)

    # 统计信号分布
    spark.sql(f"""
        WITH ma_calc AS (
            SELECT stock_code, trade_date, close_price, volume,
                   AVG(close_price) OVER (
                       PARTITION BY stock_code ORDER BY trade_date
                       ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                   ) AS ma5,
                   AVG(close_price) OVER (
                       PARTITION BY stock_code ORDER BY trade_date
                       ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                   ) AS ma10
            FROM stock_analysis.stock_daily
            {where_clause}
        ),
        signals AS (
            SELECT stock_code, trade_date, ma5, ma10,
                   CASE
                       WHEN ma5 > ma10 AND LAG(ma5) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) <= LAG(ma10) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) THEN 'GOLDEN_CROSS'
                       WHEN ma5 < ma10 AND LAG(ma5) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) >= LAG(ma10) OVER (
                           PARTITION BY stock_code ORDER BY trade_date
                       ) THEN 'DEATH_CROSS'
                       ELSE 'NORMAL'
                   END AS cross_signal
            FROM ma_calc
            WHERE ma5 IS NOT NULL AND ma10 IS NOT NULL
        )
        SELECT cross_signal, COUNT(*) AS cnt,
               COUNT(DISTINCT stock_code) AS stock_count
        FROM signals
        WHERE cross_signal IN ('GOLDEN_CROSS', 'DEATH_CROSS')
        GROUP BY cross_signal
        ORDER BY cnt DESC
    """).show(truncate=False)

    return df


def save_results(df):
    """结果写入 HDFS Parquet"""
    save_dataframe(df, OUTPUT_PATHS["ma_trend"])


def main():
    parser = argparse.ArgumentParser(description="均线趋势分析")
    parser.add_argument("--start-date", default=None, help="起始日期，如 2026-01-01")
    parser.add_argument("--end-date", default=None, help="结束日期，如 2026-05-08")
    args = parser.parse_args()

    spark = create_spark_session("MATrend")
    try:
        spark.sql("USE stock_analysis")
        print("开始计算均线趋势...")
        result_df = compute_ma_trend(spark, args.start_date, args.end_date)
        print(f"共 {result_df.count()} 个交叉信号")
        save_results(result_df)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
