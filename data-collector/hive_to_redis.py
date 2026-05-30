"""
Hive→Redis 全市场管道 — 包含所有采集的真实数据
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
        c = conn.cursor(); c.execute(sql)
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close(); return rows
    except Exception as e:
        print(f'  SQL FAIL: {e}'); return []

def put(k, data, ttl):
    if data: R.setex(k, ttl, json.dumps(data, ensure_ascii=False, default=str)); return len(data)
    return 0

def sync():
    t0 = time.time()
    # ========== 1. 原有 Hive 表数据 ==========
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
        put(key, hq(sql), ttl)

    # ========== 2. 新增 Hive 表数据（实时采集）==========
    # 腾讯实时行情 → 更新 stock_basic 详细信息
    rows = hq("SELECT stock_code, stock_name, pe_ttm, pb, mcap_yi, turnover_pct, change_pct FROM tencent_quote")
    if rows:
        for rw in rows: put(f'market:detail_{rw["stock_code"]}', [rw], HH)
        print(f'  detail_*: {len(rows)} stocks')

    # 个股资金流向 → market:fund_flow_{code}
    flow = hq("SELECT stock_code, trade_date, main_net, small_net, mid_net, large_net, super_net FROM stock_fund_flow")
    if flow:
        by = {}
        for rec in flow: by.setdefault(rec['stock_code'], []).append(rec)
        for code, rows in by.items(): put(f'market:fund_flow_{code}', rows, HH)
        print(f'  fund_flow: {len(by)} stocks x {len(flow)} records')

    # 限售解禁 → market:lockup_{code}
    lu = hq("SELECT stock_code, free_date, lockup_type, shares, ratio FROM stock_lockup")
    if lu:
        by = {}
        for rec in lu: by.setdefault(rec['stock_code'], []).append(rec)
        for code, rows in by.items(): put(f'market:lockup_{code}', rows, DD)
        # 汇总
        upc = [{'stock_code': r['stock_code'], 'lockupDate': r['free_date'], 'shares': r['shares']} for r in lu[:50]]
        put('market:lockup_upcoming', upc, DD)
        print(f'  lockup: {len(by)} stocks x {len(lu)} records')

    # 行业对比
    ind = hq("SELECT industry, code, change_pct, up_count, down_count FROM industry_compare")
    put('market:industry_compare', ind, HH)
    print(f'  industry_compare: {len(ind)} industries')

    # 个股新闻 → market:news_{code}  
    news = hq("SELECT stock_code, title, content, publish_time, source FROM stock_news")
    if news:
        by = {}
        for rec in news: by.setdefault(rec['stock_code'], []).append(rec)
        for code, rows in by.items(): put(f'market:news_{code}', rows, DD)
        print(f'  stock_news: {len(by)} stocks x {len(news)} records')

    # ========== 3. K线全量 ==========
    raw = hq("SELECT stock_code, trade_date, open, high, low, close, volume, amount, change_pct FROM stock_daily LIMIT 332520")
    if raw:
        by = {}
        for rec in raw: by.setdefault(rec['stock_code'], []).append(rec)
        for code, kls in by.items():
            R.setex(f'market:kline_{code}', HH, json.dumps(kls, ensure_ascii=False, default=str))
        print(f'  kline: {len(by)} stocks x {sum(len(v) for v in by.values())} records')

    print(f'[{time.strftime("%H:%M:%S")}] 全量同步: {R.dbsize()} key ({time.time()-t0:.0f}s)')

if __name__ == '__main__':
    print('=== Hive→Redis 全市场管道（含实时采集数据） ===')
    sync()
    while True:
        time.sleep(300)
        sync()
