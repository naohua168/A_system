"""
Spark 实时技术指标计算
从 HDFS 读取日K线数据 → 计算技术指标 (MA, MACD, RSI) → 输出到 HDFS/MySQL

用法:
    spark-submit --master local[2] realtime_indicator.py \
        --input /user/hadoop/stock_data/staging/daily/ \
        --output /user/hadoop/stock_data/analysis/indicators/
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, TimestampType

# 修复: 使用 pathlib 代替 rsplit("/")，兼容 Windows 反斜杠路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spark_config import create_spark_session, save_dataframe, OUTPUT_PATHS


def load_stock_daily(spark, data_path: str):
    """加载日K线 CSV 数据"""
    df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .csv(data_path)

    # 统一列名
    df = df.withColumnRenamed("trade_date", "date") \
        .withColumnRenamed("open_price", "open") \
        .withColumnRenamed("high_price", "high") \
        .withColumnRenamed("low_price", "low") \
        .withColumnRenamed("close_price", "close")

    # 确保数值列类型正确
    for col_name in ["open", "high", "low", "close", "volume", "amount"]:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(DoubleType()))

    # 添加日期分区
    if "date" in df.columns:
        df = df.withColumn("date_parsed", F.to_date(F.col("date"), "yyyy-MM-dd"))

    return df


def calculate_ma(df, stock_code: str, periods: list = None):
    """计算移动平均线 (MA5, MA10, MA20, MA60)"""
    if periods is None:
        periods = [5, 10, 20, 60]

    stock_df = df.filter(F.col("stock_code") == stock_code) \
        .orderBy("date")

    window = Window.orderBy("date").rowsBetween(-999, 0)

    for p in periods:
        ma_col = f"MA{p}"
        stock_df = stock_df.withColumn(
            ma_col,
            F.avg("close").over(
                Window.orderBy("date").rowsBetween(-p + 1, 0)
            )
        )

    return stock_df.select(
        "date", "stock_code", "close", *[f"MA{p}" for p in periods]
    )


def calculate_macd(df, stock_code: str):
    """计算 MACD 指标 (12, 26, 9)"""
    stock_df = df.filter(F.col("stock_code") == stock_code) \
        .orderBy("date")

    w = Window.orderBy("date")

    # EMA12 = 前一日EMA12 × 11/13 + 今日收盘价 × 2/13
    ema12_col = F.when(
        F.row_number().over(w) == 1,
        F.col("close")
    ).otherwise(
        F.lit(None)
    )
    stock_df = stock_df.withColumn("_ema12_raw", ema12_col)

    ema26_col = F.when(
        F.row_number().over(w) == 1,
        F.col("close")
    ).otherwise(
        F.lit(None)
    )
    stock_df = stock_df.withColumn("_ema26_raw", ema26_col)

    # 由于 Spark SQL 窗口函数限制，MACD 精确计算建议用 Pandas UDF
    # 这里提供近似计算: EMA ≈ 加权移动平均
    stock_df = stock_df.withColumn(
        "EMA12",
        F.avg("close").over(Window.orderBy("date").rowsBetween(-11, 0))
    ).withColumn(
        "EMA26",
        F.avg("close").over(Window.orderBy("date").rowsBetween(-25, 0))
    ).withColumn(
        "DIF",
        F.col("EMA12") - F.col("EMA26")
    ).withColumn(
        "DEA",
        F.avg("DIF").over(Window.orderBy("date").rowsBetween(-8, 0))
    ).withColumn(
        "MACD",
        (F.col("DIF") - F.col("DEA")) * 2
    )

    return stock_df.select(
        "date", "stock_code", "close",
        "EMA12", "EMA26", "DIF", "DEA", "MACD"
    )


def calculate_rsi(df, stock_code: str, period: int = 14):
    """计算 RSI 指标"""
    stock_df = df.filter(F.col("stock_code") == stock_code) \
        .orderBy("date")

    # 计算每日价格变化
    w = Window.orderBy("date")
    stock_df = stock_df.withColumn(
        "price_change",
        F.col("close") - F.lag("close", 1).over(w)
    )

    # 分别计算涨幅和跌幅
    stock_df = stock_df.withColumn(
        "gain",
        F.when(F.col("price_change") > 0, F.col("price_change")).otherwise(0)
    ).withColumn(
        "loss",
        F.when(F.col("price_change") < 0, -F.col("price_change")).otherwise(0)
    )

    # 计算平均涨幅和平均跌幅
    stock_df = stock_df.withColumn(
        "avg_gain",
        F.avg("gain").over(Window.orderBy("date").rowsBetween(-period + 1, 0))
    ).withColumn(
        "avg_loss",
        F.avg("loss").over(Window.orderBy("date").rowsBetween(-period + 1, 0))
    )

    # RSI = 100 - 100 / (1 + RS)
    stock_df = stock_df.withColumn(
        "RS",
        F.when(F.col("avg_loss") > 0,
               F.col("avg_gain") / F.col("avg_loss")).otherwise(0)
    ).withColumn(
        "RSI",
        F.when(F.col("RS").isNotNull(),
               100 - 100 / (1 + F.col("RS"))).otherwise(50)
    )

    return stock_df.select("date", "stock_code", "close", "RSI")


def save_to_hdfs(df, output_path: str, mode: str = "overwrite"):
    """保存计算结果到 HDFS Parquet"""
    save_dataframe(df, output_path, mode)


def main():
    parser = argparse.ArgumentParser(description="Spark 实时技术指标计算")
    parser.add_argument("--input", required=True, help="日K线数据 HDFS 路径")
    parser.add_argument("--output", default=OUTPUT_PATHS["realtime_indicator"],
                        help="指标结果 HDFS 输出路径")
    parser.add_argument("--code", default="000001", help="股票代码")
    parser.add_argument("--indicators", nargs="+",
                        default=["ma", "macd", "rsi"],
                        help="要计算的指标: ma macd rsi")
    args = parser.parse_args()

    spark = create_spark_session("StockRealTimeIndicator", with_hive=False)
    try:
        print(f"📥 加载数据: {args.input}")
        df = load_stock_daily(spark, args.input)
        print(f"   共 {df.count()} 条记录")

        stock_code = args.code

        if "ma" in args.indicators:
            print(f"\n📈 计算移动平均线 (MA5,10,20,60) [{stock_code}]")
            ma_df = calculate_ma(df, stock_code)
            ma_df.show(10)
            save_to_hdfs(ma_df, f"{args.output}/ma/{stock_code}")

        if "macd" in args.indicators:
            print(f"\n📊 计算 MACD [{stock_code}]")
            macd_df = calculate_macd(df, stock_code)
            macd_df.show(10)
            save_to_hdfs(macd_df, f"{args.output}/macd/{stock_code}")

        if "rsi" in args.indicators:
            print(f"\n📉 计算 RSI(14) [{stock_code}]")
            rsi_df = calculate_rsi(df, stock_code)
            rsi_df.show(10)
            save_to_hdfs(rsi_df, f"{args.output}/rsi/{stock_code}")

        print("\n✅ 技术指标计算完成")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
