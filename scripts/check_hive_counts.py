"""检查 Hive 数据量"""
import sys
sys.path.insert(0, '/app/pylib')
from pyhive import hive

conn = hive.connect(host='hive-server', port=10000)
c = conn.cursor()

for t in ['stock_basic', 'stock_daily', 'fund_basic', 'fund_list', 'info_cls_news']:
    try:
        c.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'{t}: {c.fetchone()[0]}')
    except: pass

try:
    c.execute('SELECT COUNT(DISTINCT stock_code) FROM stock_daily')
    print(f'stock_daily unique stocks: {c.fetchone()[0]}')
except: pass

try:
    c.execute('SELECT COUNT(DISTINCT stock_code) FROM stock_basic')
    print(f'stock_basic unique stocks: {c.fetchone()[0]}')
except: pass

conn.close()
