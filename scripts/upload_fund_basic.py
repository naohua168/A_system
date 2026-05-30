"""上传 fund_basic 到 HDFS 并建 Hive 表"""
import sys
sys.path.insert(0, '/app/pylib')
import requests, json

# 上传到 HDFS
data = open('/data/raw/fund_basic_20260528_145531.csv', 'rb').read()
url = 'http://namenode:9870/webhdfs/v1/user/hadoop/stock_data/fund/basic/fund_basic.csv?op=CREATE&overwrite=true&user.name=hadoop'
r = requests.put(url, allow_redirects=False)
loc = r.headers.get('Location', '')
if loc:
    r2 = requests.put(loc, data=data)
    print(f'上传完成: {len(data)} bytes, status={r2.status_code}')
else:
    print(f'上传失败: {r.status_code}')

# 创建 Hive 表
from pyhive import hive
conn = hive.connect(host='hive-server', port=10000)
c = conn.cursor()

ddl = """
CREATE EXTERNAL TABLE IF NOT EXISTS fund_basic (
    fund_code STRING, fund_name STRING, fund_type STRING,
    company STRING, manager STRING, establish_date STRING,
    nav DOUBLE, accumulated_nav DOUBLE, scale DOUBLE, status INTEGER
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/basic'
TBLPROPERTIES ('skip.header.line.count' = '1')
"""
c.execute(ddl)
print('Hive 表 fund_basic 创建完成')

c.execute('SELECT COUNT(*) FROM fund_basic')
print(f'fund_basic 数据量: {c.fetchone()[0]}')
conn.close()
