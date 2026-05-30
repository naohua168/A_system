"""
Hive→Redis 管道 — 全市场数据
"""
import sys, time, json
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

R = redis.Redis(host='redis', port=6379, db=0)
DD = 86400; HH = 3600

def hq(sql):
    try:
        conn = hive.connect(host='hive-server', port=10000)
        c = conn.cursor()
        c.execute(sql)
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f'  SQL FAIL: {e}')
        return []

def put(k, data, ttl):
    if data: R.setex(k, ttl, json.dumps(data, ensure_ascii=False, default=str)); return len(data)
    return 0

def sync():
    t0 = time.time()
    total = 0

    # 1. 静态数据 (前端展示用200条即可)
    for key, sql, ttl in [
        ('market:stock_basic', 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200', HH),
        ('market:northbound', 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20', DD),
        ('market:cls_news', 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100', DD),
        ('market:global_news', 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50', DD),
        ('market:fund_nav', 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100', DD),
        ('market:fund_list', "SELECT fund_code, fund_name, fund_type, company, scale FROM fund_basic WHERE scale>0 ORDER BY scale DESC LIMIT 500", DD),
        ('market:hot_reason', 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100', HH),
        ('market:sector_ranking', 'SELECT stock_code, stock_name, mcap_yi, turnover_pct FROM stock_basic ORDER BY mcap_yi DESC LIMIT 200', HH),
    ]:
        n = put(key, hq(sql), ttl)
        total += n
        print(f'  {key}: {n}')

    # 2. K线 (全市场 332520 条, 分批读取)
    print('  读取 stock_daily 全量K线...')
    raw = hq("SELECT stock_code, trade_date, open, high, low, close, volume, amount, change_pct FROM stock_daily LIMIT 332520")
    if raw:
        by = {}
        for rec in raw:
            by.setdefault(rec['stock_code'], []).append(rec)
        for code, kls in by.items():
            R.setex(f'market:kline_{code}', HH, json.dumps(kls, ensure_ascii=False, default=str))
        print(f'  kline: {len(by)} stocks x {sum(len(v) for v in by.values())} records')
        total += sum(len(v) for v in by.values())

    print(f'[{time.strftime("%H:%M:%S")}] 全量同步: {total}条, {time.time()-t0:.0f}s')

if __name__ == '__main__':
    print('=== Hive→Redis 全市场管道 ===')
    sync()
    while True:
        time.sleep(300)
        sync()
