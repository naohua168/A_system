"""
相关系数矩阵计算
使用 Spark corr() 函数按行业分组批量计算股票间相关系数

用法:
    spark-submit \
        --master local[2] \
        --conf spark.sql.catalogImplementation=hive \
        correlation.py

    支持指定行业:
    spark-submit ... correlation.py --industry 银行
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def create_spark_with_hive():
    """创建支持 Hive 的 Spark 会话"""
    return SparkSession.builder \
        .appName("StockCorrelation") \
        .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
        .config("hive.metastore.uris", "thrift://hive-metastore:9083") \
        .config("spark.sql.catalogImplementation", "hive") \
        .enableHiveSupport() \
        .getOrCreate()


def compute_correlation(spark, industry=None):
    """
    按行业分组，计算每对股票之间的收益率相关系数。
    步骤：
    1. 先计算出每日收益率 change_pct（已预计算）
    2. 按行业JOIN stock_basic 获取行业信息
    3. 自关联 stock_daily，对每对 (code_a, code_b) 用 corr() 计算相关系数
    """
    condition = ""
    if industry:
        condition = f"AND b.industry = '{industry}'"

    df = spark.sql(f"""
        WITH industry_stocks AS (
            SELECT code, name, industry
            FROM stock_analysis.stock_basic
            WHERE industry IS NOT NULL {condition}
        ),
        daily_returns AS (
            SELECT stock_code, trade_date, change_pct
            FROM stock_analysis.stock_daily
            WHERE change_pct IS NOT NULL
        ),
        stock_pairs AS (
            SELECT a.code AS code_a,
                   a.name AS name_a,
                   b.code AS code_b,
                   b.name AS name_b,
                   a.industry
            FROM industry_stocks a
            JOIN industry_stocks b
              ON a.industry = b.industry
             AND a.code < b.code
        )
        SELECT p.industry,
               p.code_a, p.name_a,
               p.code_b, p.name_b,
               ROUND(F.corr(da.change_pct, db.change_pct), 4) AS correlation
        FROM stock_pairs p
        JOIN daily_returns da ON p.code_a = da.stock_code
        JOIN daily_returns db ON p.code_b = db.stock_code
           AND da.trade_date = db.trade_date
        GROUP BY p.industry, p.code_a, p.name_a, p.code_b, p.name_b
        HAVING COUNT(*) >= 60
        ORDER BY ABS(correlation) DESC
    """)

    title = f"行业: {industry}" if industry else "全行业"
    print(f"\n{title} 相关系数 Top60:")
    df.show(60, truncate=False)
    return df


def compute_industry_avg_correlation(spark, industry=None):
    """计算行业平均相关系数"""
    condition = f"WHERE b.industry = '{industry}'" if industry else "WHERE b.industry IS NOT NULL"

    df = spark.sql(f"""
        SELECT b.industry,
               COUNT(DISTINCT b.code) AS stock_count,
               ROUND(AVG(d1.change_pct * d2.change_pct)
                     OVER (PARTITION BY b.industry), 4) AS avg_corr_approx
        FROM stock_analysis.stock_daily d1
        JOIN stock_analysis.stock_daily d2
          ON d1.trade_date = d2.trade_date AND d1.stock_code < d2.stock_code
        JOIN stock_analysis.stock_basic b ON d1.stock_code = b.code
        {condition}
        LIMIT 10
    """)
    print("\n行业平均相关性（简化统计）:")
    spark.sql(f"""
        SELECT s1.industry,
               COUNT(DISTINCT s1.code) AS stock_count,
               ROUND(AVG(s1.corr_avg), 4) AS avg_correlation
        FROM (
            SELECT b.industry, d.stock_code,
                   ROUND(AVG(d.change_pct), 4) AS corr_avg
            FROM stock_analysis.stock_daily d
            JOIN stock_analysis.stock_basic b ON d.stock_code = b.code
            {condition.replace('WHERE ', 'WHERE ')}
            GROUP BY b.industry, d.stock_code
        ) s1
        GROUP BY s1.industry
        ORDER BY avg_correlation DESC
    """).show(truncate=False)


def save_results(df):
    """结果写入 HDFS Parquet"""
    output_path = "/user/hadoop/stock_data/analysis/spark/correlation/"
    df.write.mode("overwrite") \
        .option("compression", "snappy") \
        .parquet(output_path)
    print(f"已保存到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="相关系数矩阵计算")
    parser.add_argument("--industry", default=None, help="指定行业，如 银行")
    args = parser.parse_args()

    spark = create_spark_with_hive()
    try:
        spark.sql("USE stock_analysis")
        print("开始计算相关系数矩阵...")
        result_df = compute_correlation(spark, args.industry)
        print(f"共 {result_df.count()} 对股票")
        save_results(result_df)
        compute_industry_avg_correlation(spark, args.industry)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
