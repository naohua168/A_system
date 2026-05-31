"""快速填充 Redis 关键数据（直接从 Hive 查询）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__) if '__file__' in dir() else '/app', 'pylib'))
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import json, redis, re

r = redis.Redis(host='redis', port=6379, db=0)
conn = hive.connect(host='hive-server', port=10000)
c = conn.cursor()

def to_camel_case(snake: str) -> str:
    """snake_case → camelCase"""
    parts = snake.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

queries = [
    ('market:stock_basic', 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200', 3600),
    ('market:northbound', 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20', 86400),
    ('market:cls_news', 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100', 86400),
    ('market:global_news', 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50', 86400),
    ('market:fund_nav', 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100', 86400),
    ('market:fund_list', "SELECT fund_code, scale FROM fund_list WHERE CAST(scale AS STRING) RLIKE '^[0-9]+\\\\.[0-9]+$' ORDER BY CAST(scale AS DOUBLE) DESC LIMIT 200", 86400),
    ('market:hot_reason', 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date, close_price, change, change_pct, turnover_pct, amount, volume, big_net_pct, market, source FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100', 3600),
]

total = 0
for key, sql, ttl in queries:
    try:
        c.execute(sql)
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, row)) for row in c.fetchall()]
        if rows:
            rows = [{to_camel_case(k): v for k, v in row.items()} for row in rows]
            r.setex(key, ttl, json.dumps(rows, ensure_ascii=False, default=str))
            total += len(rows)
            print(f'  {key}: {len(rows)} rows (TTL={ttl}s)')
    except Exception as e:
        print(f'  {key}: SKIP ({e})')

conn.close()
print(f'\nTotal: {total} items synced to Redis')
