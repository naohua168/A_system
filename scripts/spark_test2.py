"""测试 stock_daily 表查询"""
from pyspark.sql import SparkSession
import sys
spark = SparkSession.builder.appName("TestDaily").master("spark://spark-master:7077").enableHiveSupport().getOrCreate()
df = spark.sql("SELECT COUNT(*) as cnt FROM stock_daily")
print(f"stock_daily: {df.collect()[0].cnt}")
df2 = spark.sql("SELECT stock_code, COUNT(*) as days FROM stock_daily GROUP BY stock_code ORDER BY days DESC LIMIT 5")
for r in df2.collect():
    print(f"  {r.stock_code}: {r.days} days")
spark.stop()
