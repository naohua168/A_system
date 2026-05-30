"""Spark Hive 连通性测试"""
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("HiveTest") \
    .master("spark://spark-master:7077") \
    .enableHiveSupport() \
    .getOrCreate()

try:
    tables = spark.sql("SHOW TABLES").collect()
    print(f"Hive 表 ({len(tables)}):")
    for t in tables:
        print(f"  {t.tableName}")

    df = spark.sql("SELECT COUNT(*) as cnt FROM stock_basic")
    print(f"\nstock_basic: {df.collect()[0].cnt} 行")
except Exception as e:
    print(f"FAILED: {e}")

spark.stop()
