#!/usr/bin/env python3
"""从容器上传CSV到HDFS并加载到Hive"""
import subprocess, os

# 检查文件
for f in ['/tmp/stock_basic.csv','/tmp/stock_daily.csv']:
    print(f'{f}: {os.path.getsize(f)} bytes')

# 上传basic
r = subprocess.run(
    ['bash','-c','cat /tmp/stock_basic.csv | docker exec -i namenode hdfs dfs -put -f - /user/hadoop/stock_data/basic/stock_basic.csv'],
    capture_output=True, text=True, timeout=30)
print(f'basic upload: {r.returncode} | {r.stderr.strip()[:80] if r.stderr.strip() else "OK"}')

# 上传daily
r2 = subprocess.run(
    ['bash','-c','cat /tmp/stock_daily.csv | docker exec -i namenode hdfs dfs -put -f - /user/hadoop/stock_data/daily/stock_daily.csv'],
    capture_output=True, text=True, timeout=30)
print(f'daily upload: {r2.returncode} | {r2.stderr.strip()[:80] if r2.stderr.strip() else "OK"}')

# 验证
r3 = subprocess.run(['bash','-c','docker exec namenode hdfs dfs -ls /user/hadoop/stock_data/basic/ && docker exec namenode hdfs dfs -ls /user/hadoop/stock_data/daily/'],
    capture_output=True, text=True, timeout=30)
print(f'\nHDFS files:')
for l in r3.stdout.split('\n'):
    if 'stock_' in l: print(f'  {l.strip()}')
