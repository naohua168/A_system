#!/usr/bin/env python3
"""从宿主机上传数据到HDFS + 加载到Hive"""
import subprocess, sys

# Step 1: 从data-collector复制CSV到本地临时目录
import tempfile, pathlib
tmp = pathlib.Path(tempfile.gettempdir())
subprocess.run(['docker','cp','data-collector:/tmp/stock_basic.csv',str(tmp / 'stock_basic.csv')], check=True)
subprocess.run(['docker','cp','data-collector:/tmp/stock_daily.csv',str(tmp / 'stock_daily.csv')], check=True)
print("Copied from container")

# Step 2: 上传到HDFS (用stdin方式)
csv_basic = tmp / 'stock_basic.csv'
csv_daily = tmp / 'stock_daily.csv'

with open(str(csv_basic), 'rb') as f:
    r = subprocess.run(['docker','exec','-i','namenode','hdfs','dfs','-put','-f','-','/user/hadoop/stock_data/basic/stock_basic.csv'],
        stdin=f, capture_output=True, text=True, timeout=30)
    print(f'basic HDFS: {r.returncode} {r.stderr.strip()[:60] if r.stderr.strip() else "OK"}')

with open(str(csv_daily), 'rb') as f:
    r = subprocess.run(['docker','exec','-i','namenode','hdfs','dfs','-put','-f','-','/user/hadoop/stock_data/daily/stock_daily.csv'],
        stdin=f, capture_output=True, text=True, timeout=30)
    print(f'daily HDFS: {r.returncode} {r.stderr.strip()[:60] if r.stderr.strip() else "OK"}')

# Step 3: 加载到Hive
r = subprocess.run(['docker','exec','hive-server','hive','-e',
    "LOAD DATA INPATH '/user/hadoop/stock_data/basic/stock_basic.csv' OVERWRITE INTO TABLE stock_analysis.stock_basic"],
    capture_output=True, text=True, timeout=30)
print(f'Hive basic: {r.returncode}')
for l in r.stderr.split('\n'):
    if 'FAILED' in l or 'Error' in l: print(f'  {l.strip()}')

r = subprocess.run(['docker','exec','hive-server','hive','-e',
    "LOAD DATA INPATH '/user/hadoop/stock_data/daily/stock_daily.csv' OVERWRITE INTO TABLE stock_analysis.stock_daily PARTITION(dt='20260522')"],
    capture_output=True, text=True, timeout=30)
print(f'Hive daily: {r.returncode}')
for l in r.stderr.split('\n'):
    if 'FAILED' in l or 'Error' in l: print(f'  {l.strip()}')

# Step 4: 验证
r = subprocess.run(['docker','exec','hive-server','hive','-e',
    'USE stock_analysis; SELECT COUNT(*) FROM stock_basic; SELECT COUNT(*) FROM stock_daily;'],
    capture_output=True, text=True, timeout=30)
print(f'\nHive verify:')
for l in r.stdout.split('\n'):
    if l.strip().isdigit(): print(f'  {l.strip()} rows')

print('\nDone')
