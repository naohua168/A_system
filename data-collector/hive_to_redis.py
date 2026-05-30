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

def sync_mock(r):
    """模拟数据（无Hive表）—— 指数/行业/龙虎榜"""
    mock = {
        'market:index_list': [
            {"index_code":"000001","index_name":"上证指数","price":3350.42,"change_pct":0.56},
            {"index_code":"399001","index_name":"深证成指","price":11256.78,"change_pct":1.23},
            {"index_code":"399006","index_name":"创业板指","price":2356.89,"change_pct":1.96},
            {"index_code":"000688","index_name":"科创50","price":1289.45,"change_pct":2.15},
            {"index_code":"000300","index_name":"沪深300","price":4123.56,"change_pct":0.78},
        ],
        'market:industry_treemap': [
            {"industry":"金融","mcap_yi":125000,"change_pct":1.2,"stocks":120},
            {"industry":"科技","mcap_yi":98000,"change_pct":2.5,"stocks":200},
            {"industry":"医药","mcap_yi":65000,"change_pct":0.8,"stocks":150},
            {"industry":"消费","mcap_yi":72000,"change_pct":1.5,"stocks":180},
            {"industry":"新能源","mcap_yi":55000,"change_pct":3.2,"stocks":90},
        ],
        'market:industry_compare': [
            {"industry":"金融","avg_change":1.2,"total_amount":580,"stock_count":120},
            {"industry":"科技","avg_change":2.5,"total_amount":720,"stock_count":200},
            {"industry":"医药","avg_change":0.8,"total_amount":320,"stock_count":150},
            {"industry":"新能源","avg_change":3.2,"total_amount":450,"stock_count":90},
        ],
        'market:dragon_tiger': [
            {"stock_code":"600000","stock_name":"浦发银行","buy_amount":5.2,"sell_amount":3.8,"net_amount":1.4,"reason":"日涨幅偏离值达7%"},
            {"stock_code":"600519","stock_name":"贵州茅台","buy_amount":8.5,"sell_amount":6.2,"net_amount":2.3,"reason":"连续三日涨幅偏离值累计达20%"},
        ],
    }
    n = 0
    for key, data in mock.items():
        n += put(r, key, data, TTL_DAY)
    return n


def sync_static(r):
    """静态数据 — 24h TTL"""
    total = 0
    q = [
        ('market:stock_basic', 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200', TTL_HOUR),
        ('market:northbound', 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20', TTL_DAY),
        ('market:cls_news', 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100', TTL_DAY),
        ('market:global_news', 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50', TTL_DAY),
        ('market:fund_nav', 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100', TTL_DAY),
        ('market:fund_list', "SELECT fund_code, MAX(scale) AS scale FROM fund_list WHERE CAST(scale AS STRING) RLIKE '^[0-9]+\\\\.[0-9]+$' GROUP BY fund_code ORDER BY CAST(MAX(scale) AS DOUBLE) DESC LIMIT 200", TTL_DAY),
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
        total = sync_mock(r)
        total += sync_static(r)
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
