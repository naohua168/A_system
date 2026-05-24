#!/usr/bin/env python3
"""从MySQL导出数据到CSV → 加载到HDFS/Hive"""
import pymysql, csv, os, subprocess, time

conn = pymysql.connect(host='mysql',port=3306,user='root',password='hadoop123',database='stock_analysis',charset='utf8mb4')
c=conn.cursor()

print("=== Step 1: Export MySQL -> CSV ===")
# stock_basic
c.execute("SELECT stock_code,stock_name,IFNULL(industry,'未知'),IFNULL(market,'A'),IFNULL(pe,0) FROM stock")
with open('/tmp/stock_basic.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    for r in c.fetchall(): w.writerow(r)
print(f"  stock_basic.csv: {os.path.getsize('/tmp/stock_basic.csv')} bytes")

# stock_daily (trade_date列复制给dt做分区)
c.execute("SELECT stock_code,trade_date,open_price,close_price,high_price,low_price,pre_close,volume,amount,change_percent,turnover_rate,trade_date FROM stock_daily")
with open('/tmp/stock_daily.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    for r in c.fetchall(): w.writerow(r)
print(f"  stock_daily.csv: {os.path.getsize('/tmp/stock_daily.csv')} bytes")
c.close();conn.close()

print("\n=== Step 2: Copy to HDFS ===")
subprocess.run(['docker','cp','/tmp/stock_basic.csv','namenode:/tmp/'],capture_output=True)
subprocess.run(['docker','cp','/tmp/stock_daily.csv','namenode:/tmp/'],capture_output=True)

# 在namenode上put到HDFS
r1 = subprocess.run(['docker','exec','namenode','hdfs','dfs','-put','-f','/tmp/stock_basic.csv','/user/hadoop/stock_data/stock_basic.csv'],capture_output=True,text=True)
print(f"  stock_basic -> HDFS: {r1.returncode}")
r2 = subprocess.run(['docker','exec','namenode','hdfs','dfs','-mkdir','-p','/user/hadoop/stock_data/daily'],capture_output=True)
r3 = subprocess.run(['docker','exec','namenode','hdfs','dfs','-put','-f','/tmp/stock_daily.csv','/user/hadoop/stock_data/daily/'],capture_output=True,text=True)
print(f"  stock_daily -> HDFS: {r3.returncode}")

print("\n=== Step 3: Load into Hive ===")
# stock_basic (无分区)
hive_cmd1 = "LOAD DATA INPATH '/user/hadoop/stock_data/stock_basic.csv' OVERWRITE INTO TABLE stock_analysis.stock_basic"
r4 = subprocess.run(['docker','exec','hive-server','hive','-e',hive_cmd1],capture_output=True,text=True,timeout=30)
print(f"  stock_basic -> Hive: {r4.returncode}")
for l in r4.stderr.split('\n'):
    if 'FAILED' in l or 'Error' in l: print(f"    {l}")

# stock_daily (分区)
hive_cmd2 = "LOAD DATA INPATH '/user/hadoop/stock_data/daily/stock_daily.csv' OVERWRITE INTO TABLE stock_analysis.stock_daily PARTITION(dt='20260522')"
r5 = subprocess.run(['docker','exec','hive-server','hive','-e',hive_cmd2],capture_output=True,text=True,timeout=30)
print(f"  stock_daily -> Hive: {r5.returncode}")

# 验证
r6 = subprocess.run(['docker','exec','hive-server','hive','-e','USE stock_analysis; SELECT COUNT(*) FROM stock_basic; SELECT COUNT(*) FROM stock_daily;'],capture_output=True,text=True,timeout=30)
print(f"\n=== 验证 ===")
for l in r6.stdout.split('\n'):
    if l.strip().isdigit(): print(f"  行数: {l.strip()}")

print("\n✅ Hive数据加载完成")
