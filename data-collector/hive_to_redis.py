"""Hive→Redis 管道 — 大数据层正式管道（替代 auto_seed.py）"""
import sys, time, json, os
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

REDIS_HOST = 'redis'
HIVE_HOST = 'hive-server'
TTL_DAY = 86400
TTL_HOUR = 3600

CACHE = {}  # TTL追踪，避免每次全量刷新

def put(r, key, data, ttl):
    if not data: return 0
    r.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
    return len(data)

def hive_select(sql):
    conn = hive.connect(host=HIVE_HOST, port=10000, timeout=60)
    c = conn.cursor()
    c.execute(sql)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return rows

def sync_static(r):
    """静态数据 — 24h TTL"""
    total = 0
    q = [
        ('market:stock_basic', 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200', TTL_HOUR),
        ('market:northbound', 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20', TTL_DAY),
        ('market:cls_news', 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100', TTL_DAY),
        ('market:global_news', 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50', TTL_DAY),
        ('market:fund_nav', 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100', TTL_DAY),
        ('market:fund_list', "SELECT fund_code, scale FROM fund_list WHERE CAST(scale AS STRING) RLIKE '^[0-9]+\\\\.[0-9]+$' ORDER BY CAST(scale AS DOUBLE) DESC LIMIT 200", TTL_DAY),
        ('market:hot_reason', 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date, close_price, change, change_pct, turnover_pct, amount, volume, big_net_pct, market, source FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100', TTL_HOUR),
        ('market:sector_ranking', 'SELECT stock_code, stock_name, mcap_yi, turnover_pct FROM stock_basic ORDER BY mcap_yi DESC LIMIT 200', TTL_HOUR),
    ]
    for key, sql, ttl in q:
        try:
            rows = hive_select(sql)
            n = put(r, key, rows, ttl)
            if n: total += n
        except Exception as e:
            pass  # 已有缓存不丢失
    return total

def sync_kline(r):
    """K线 — 从 stock_daily 按股票拆分"""
    try:
        rows = hive_select("SELECT stock_code, trade_date, open, high, low, close, volume, amount, change_pct FROM stock_daily LIMIT 30000")
        by_code = {}
        for rec in rows:
            code = rec["stock_code"]
            by_code.setdefault(code, []).append(rec)
        n = 0
        for code, klines in by_code.items():
            r.setex(f"market:kline_{code}", TTL_HOUR, json.dumps(klines, ensure_ascii=False, default=str))
            n += len(klines)
        return n
    except:
        return 0

def sync():
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
        total = sync_static(r)
        total += sync_kline(r)
        print(f'[{time.strftime("%H:%M:%S")}] Hive→Redis: {total}条完成')
    except Exception as e:
        print(f'[{time.strftime("%H:%M:%S")}] 失败: {e}')

if __name__ == '__main__':
    print('=== Hive→Redis 大数据层管道 ===')
    # 首次运行
    sync()
    # 定时循环
    while True:
        time.sleep(600)  # 10分钟
        sync()
