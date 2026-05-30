"""
Spark ETL 批处理 (Phase 7)
从 Hive 读取 stock_daily，计算行业排名，写回 HDFS CSV
"""
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, sum as spark_sum, count, round, desc

spark = SparkSession.builder \
    .appName("StockDailyETL") \
    .master("spark://spark-master:7077") \
    .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
    .enableHiveSupport() \
    .getOrCreate()

# 1. 从 Hive 读取 stock_daily
import sys
log = open("/tmp/etl_debug.log", "w")
df = spark.sql("SELECT * FROM stock_daily")
total = df.count()
log.write(f"stock_daily 读取: {total} 行\n")
print(f"stock_daily 读取: {total} 行", flush=True)

# 2. 按股票计算聚合指标
sector_df = df.groupBy("stock_code", "stock_name").agg(
    round(avg("change_pct"), 2).alias("avg_change_pct"),
    round(avg("close"), 2).alias("avg_close"),
    round(avg("volume"), 0).alias("avg_volume"),
    round(spark_sum("amount"), 2).alias("total_amount"),
    count("trade_date").alias("trade_days")
).orderBy(desc("avg_volume"))

sector_count = sector_df.count()
print(f"行业排行计算: {sector_count} 只股票")

# 3. 写回 HDFS（CSV格式）
from datetime import datetime
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = f"/user/hadoop/stock_data/analysis/spark/sector_ranking/daily_{ts}"
sector_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(output_path)

print(f"结果写入 HDFS: {output_path}")
print(f"写入行数: {sector_count}")

spark.stop()
