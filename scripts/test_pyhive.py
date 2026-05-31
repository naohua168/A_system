"""测试 pyhive 连接 Hive 的数据查询"""
import sys
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import time

t0 = time.time()
conn = hive.connect(host='hive-server', port=10000)
c = conn.cursor()

queries = [
    ('stock_basic', 'SELECT COUNT(*) FROM stock_basic'),
    ('cls_news', 'SELECT COUNT(*) FROM info_cls_news'),
    ('global_news', 'SELECT COUNT(*) FROM info_global_news'),
    ('northbound', 'SELECT COUNT(*) FROM signal_northbound'),
    ('fund_nav', 'SELECT COUNT(*) FROM fund_nav'),
    ('fund_list', 'SELECT COUNT(*) FROM fund_list'),
    ('hot_reason', 'SELECT COUNT(*) FROM signal_hot_reason'),
    ('stock_daily', 'SELECT COUNT(*) FROM stock_daily'),
]

for name, sql in queries:
    t = time.time()
    try:
        c.execute(sql)
        row = c.fetchone()
        print(f'  {name:15s}: {row[0]:>8} rows ({time.time()-t:.1f}s)')
    except Exception as e:
        print(f'  {name:15s}: FAILED ({e})')

conn.close()
print(f'\nTotal: {time.time()-t0:.1f}s')
