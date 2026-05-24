#!/usr/bin/env python3
"""
Spark 行业涨跌排行 - 从 MySQL 读取数据，用 Spark 分布式计算，结果写回 MySQL
实现: 采集器 → MySQL → Spark → MySQL（前端消费）
"""
import sys, time
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder \
    .appName("SectorRankingMySQL") \
    .config("spark.driver.extraClassPath", "/opt/spark/jars/mysql-connector-java.jar") \
    .getOrCreate()

jdbc_url = "jdbc:mysql://mysql:3306/stock_analysis?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true"
props = {"user": "root", "password": "hadoop123", "driver": "com.mysql.cj.jdbc.Driver"}

daily = spark.read.jdbc(jdbc_url, "stock_daily", properties=props)
stock = spark.read.jdbc(jdbc_url, "stock", properties=props)

max_date = daily.agg(F.max("trade_date")).collect()[0][0]
print(f"最新交易日: {max_date}")

# Spark 分布式计算行业排行
daily2 = daily.alias("d").filter(F.col("d.trade_date") == max_date)
stock2 = stock.alias("s").filter("s.industry IS NOT NULL AND s.industry != ''")
result = daily2.join(stock2, F.col("d.stock_code") == F.col("s.stock_code")) \
    .groupBy(F.col("s.industry").alias("industry")) \
    .agg(
        F.count("*").alias("stock_count"),
        F.round(F.avg("d.change_percent"), 2).alias("avg_change_pct"),
        F.round(F.sum("d.change_percent"), 2).alias("total_change_pct"),
        F.round(F.max("d.change_percent"), 2).alias("max_change_pct"),
        F.round(F.min("d.change_percent"), 2).alias("min_change_pct"),
        F.round(F.sum(F.when(F.col("d.change_percent") > 0, 1).otherwise(0)) * 100.0 / F.count("*"), 1).alias("up_ratio"),
    ) \
    .orderBy(F.desc("avg_change_pct"))

print(f"\nSpark 计算出 {result.count()} 个行业排行:")
result.show(50, truncate=False)

# 写回 MySQL
rows = result.collect()
import pymysql
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123',
                       database='stock_analysis', charset='utf8mb4')
cur = conn.cursor()

# 创建结果表（如果不存在）
cur.execute("""
    CREATE TABLE IF NOT EXISTS signal_spark_sector_ranking (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trade_date VARCHAR(10),
        industry VARCHAR(50),
        stock_count INT,
        avg_change_pct DECIMAL(8,2),
        total_change_pct DECIMAL(10,2),
        max_change_pct DECIMAL(8,2),
        min_change_pct DECIMAL(8,2),
        up_ratio DECIMAL(5,1),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_date_industry (trade_date, industry)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# 清空当日数据再写入
cur.execute("DELETE FROM signal_spark_sector_ranking WHERE trade_date=%s", (max_date,))
inserted = 0
for r in rows:
    try:
        cur.execute("""
            INSERT INTO signal_spark_sector_ranking 
            (trade_date, industry, stock_count, avg_change_pct, total_change_pct, max_change_pct, min_change_pct, up_ratio)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (max_date, r.industry, int(r.stock_count), float(r.avg_change_pct),
              float(r.total_change_pct), float(r.max_change_pct), float(r.min_change_pct), float(r.up_ratio)))
        inserted += 1
    except Exception as e:
        print(f"  Insert error: {e}")

conn.commit()
cur.close(); conn.close()
print(f"写回 MySQL: {inserted} 行 (表: signal_spark_sector_ranking)")

# 验证
spark.read.jdbc(jdbc_url, "signal_spark_sector_ranking", properties=props).show(5)
print(f"\n✅ 大数据管道完成: 腾讯API→MySQL→Spark→MySQL(云图)")
spark.stop()
