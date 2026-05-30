"""
Hive→Redis 管道 — 仅保留真实采集的市场数据
不生成任何模拟/伪造数据
"""
import sys, time, json
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

REDIS_HOST = 'redis'
HIVE_HOST = 'hive-server'

r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
DD = 86400   # 24h
HH = 3600    # 1h

def hive_q(sql):
    try:
        conn = hive.connect(host=HIVE_HOST, port=10000)
        c = conn.cursor()
        c.execute(sql)
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, row)) for row in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        return []

def put(key, data, ttl):
    if data:
        r.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
        return len(data)
    return 0

def sync():
    """仅同步真实Hive数据表"""
    total = 0
    queries = [
        # 股票列表 (真实)
        ('market:stock_basic', 'SELECT stock_code, stock_name FROM stock_basic ORDER BY stock_code LIMIT 200', HH),
        # 北向资金 (真实)
        ('market:northbound', 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20', DD),
        # 财联社快讯 (真实)
        ('market:cls_news', 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100', DD),
        # 全球资讯 (真实)
        ('market:global_news', 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50', DD),
        # 基金净值 (真实)
        ('market:fund_nav', 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100', DD),
        # 基金列表 (真实)
        ('market:fund_list', "SELECT fund_code, fund_name, fund_type, company, scale FROM fund_basic WHERE scale>0 ORDER BY scale DESC LIMIT 200", DD),
        # 题材热点 (真实)
        ('market:hot_reason', 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100', HH),
        # 行业排行 (来自stock_basic真实数据)
        ('market:sector_ranking', 'SELECT stock_code, stock_name, mcap_yi, turnover_pct FROM stock_basic ORDER BY mcap_yi DESC LIMIT 200', HH),
    ]
    for key, sql, ttl in queries:
        rows = hive_q(sql)
        n = put(key, rows, ttl)
        if n: total += n
        print(f'  {key}: {n} rows')

    print(f'[{time.strftime("%H:%M:%S")}] 真实数据同步完成: {total}条, Redis共{len(r.keys("market:*"))}key(不含模拟)')

if __name__ == '__main__':
    print('=== Hive→Redis 真实数据管道（无模拟数据） ===')
    sync()
    while True:
        time.sleep(600)
        sync()
