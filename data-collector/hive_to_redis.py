"""Hive→Redis 定时同步管道 — 覆盖全部 Redis key 映射"""
import sys, time, json
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

REDIS_HOST = 'redis'
HIVE_HOST = 'hive-server'

# Redis key → Hive SQL 映射
QUERIES = {
    'market:stock_basic': 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200',
    'market:northbound': 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20',
    'market:cls_news': 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100',
    'market:global_news': 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50',
    'market:fund_nav': 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100',
    'market:fund_list': 'SELECT fund_code, scale FROM fund_list ORDER BY scale DESC LIMIT 200',
    'market:hot_reason': 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date, close_price, change, change_pct, turnover_pct, amount, volume, big_net_pct, market, source FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100',
}


def sync():
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
        conn = hive.connect(host=HIVE_HOST, port=10000)
        c = conn.cursor()
        total = 0
        for key, sql in QUERIES.items():
            try:
                c.execute(sql)
                cols = [d[0] for d in c.description]
                rows = [dict(zip(cols, row)) for row in c.fetchall()]
                if rows:
                    r.setex(key, 300, json.dumps(rows, ensure_ascii=False, default=str))
                    total += len(rows)
            except Exception as e:
                print(f'  {key} ERROR: {e}')
        conn.close()
        print(f'[{time.strftime("%H:%M:%S")}] Synced {total} items to Redis')
    except Exception as e:
        print(f'[{time.strftime("%H:%M:%S")}] Sync failed: {e}')


if __name__ == '__main__':
    print('Hive->Redis pipeline started (7 tables)')
    while True:
        sync()
        time.sleep(60)
