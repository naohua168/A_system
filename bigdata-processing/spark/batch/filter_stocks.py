"""
股票筛选
根据 PE / PB / ROE / 成交量等基本面与技术面指标筛选优质股票

用法:
    spark-submit --master local[2] filter_stocks.py
    spark-submit ... filter_stocks.py --pe-max 20 --pb-max 2 --roe-min 10 --volume-min 1000000
"""

import argparse
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# 修复: 使用 pathlib 代替 rsplit("/")，兼容 Windows 反斜杠路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spark_config import create_spark_session, save_dataframe, OUTPUT_PATHS


def filter_stocks(spark, pe_max=30, pb_max=3, roe_min=8,
                  volume_min=500000, trade_date=None):
    """
    多维度筛选优质股票：
    - 基本面: PE(市盈率)、PB(市净率)、ROE(净资产收益率)
    - 技术面: 成交量、涨跌幅稳定性
    """
    date_filter = f"AND d.trade_date = '{trade_date}'" if trade_date else ""

    df = spark.sql(f"""
        WITH latest_price AS (
            SELECT stock_code, close_price, change_pct, volume, trade_date
            FROM stock_analysis.stock_daily
            WHERE close_price IS NOT NULL {date_filter.replace('AND ', 'AND ', 1) if not date_filter else date_filter}
        ),
        avg_volume AS (
            SELECT stock_code,
                   ROUND(AVG(volume), 0) AS avg_volume_30d,
                   ROUND(STDDEV(change_pct), 2) AS price_volatility
            FROM stock_analysis.stock_daily
            WHERE change_pct IS NOT NULL
            GROUP BY stock_code
        )
        SELECT l.stock_code,
               b.name,
               b.industry,
               l.trade_date,
               ROUND(l.close_price, 2) AS close_price,
               ROUND(l.change_pct, 2) AS change_pct,
               ROUND(l.volume, 0) AS volume,
               ROUND(a.avg_volume_30d, 0) AS avg_volume_30d,
               ROUND(l.volume / NULLIF(a.avg_volume_30d, 0), 2) AS vol_ratio,
               ROUND(a.price_volatility, 2) AS price_volatility,
               ROUND(b.pe, 2) AS pe,
               ROUND(b.pb, 2) AS pb,
               ROUND(b.roe, 2) AS roe,
               ROUND(b.market_cap / 1e8, 2) AS market_cap_billions,
               CASE
                   WHEN b.pe <= {pe_max} AND b.pb <= {pb_max}
                        AND b.roe >= {roe_min} AND l.volume >= {volume_min}
                   THEN 'PASS'
                   ELSE 'FAIL'
               END AS filter_result
        FROM latest_price l
        JOIN stock_analysis.stock_basic b ON l.stock_code = b.code
        LEFT JOIN avg_volume a ON l.stock_code = a.stock_code
        WHERE b.pe IS NOT NULL AND b.pb IS NOT NULL
          AND b.roe IS NOT NULL
        ORDER BY filter_result DESC, b.roe DESC, l.volume DESC
    """)

    print(f"\n股票筛选结果 (PE<={pe_max}, PB<={pb_max}, ROE>={roe_min}%, 成交量>={volume_min}):")
    df.show(50, truncate=False)

    # 统计通过/未通过数量
    df.createOrReplaceTempView("filtered_stocks")
    spark.sql("""
        SELECT filter_result, COUNT(*) AS cnt
        FROM filtered_stocks
        GROUP BY filter_result
        ORDER BY filter_result
    """).show(truncate=False)

    return df


def save_results(df):
    """结果写入 HDFS Parquet"""
    save_dataframe(df, OUTPUT_PATHS["filter_stocks"])


def main():
    parser = argparse.ArgumentParser(description="股票筛选")
    parser.add_argument("--pe-max", type=int, default=30, help="最大市盈率，默认 30")
    parser.add_argument("--pb-max", type=int, default=3, help="最大市净率，默认 3")
    parser.add_argument("--roe-min", type=int, default=8, help="最低ROE(%), 默认 8")
    parser.add_argument("--volume-min", type=int, default=500000, help="最低成交量, 默认 500000")
    parser.add_argument("--trade-date", default=None, help="交易日，默认最近")
    args = parser.parse_args()

    spark = create_spark_session("StockFilter")
    try:
        spark.sql("USE stock_analysis")
        print("开始筛选股票...")
        result_df = filter_stocks(
            spark, args.pe_max, args.pb_max, args.roe_min,
            args.volume_min, args.trade_date
        )
        pass_count = result_df.filter(F.col("filter_result") == "PASS").count()
        print(f"通过筛选: {pass_count} 只")
        save_results(result_df)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
