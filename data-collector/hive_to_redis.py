"""Hive→Redis 定时同步管道 — 简化版避免 MapReduce"""
import sys, time, json
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

REDIS_HOST = 'redis'
HIVE_HOST = 'hive-server'

QUERIES = {
    'market:stock_basic': 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200',
    'market:northbound': 'SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20',
    'market:cls_news': 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100',
    'market:global_news': 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50',
    'market:fund_nav': 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100',
    'market:fund_list': "SELECT fund_code, scale FROM fund_list WHERE CAST(scale AS STRING) RLIKE '^[0-9]+\\\\.[0-9]+$' ORDER BY CAST(scale AS DOUBLE) DESC LIMIT 200",
    'market:hot_reason': 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date, close_price, change, change_pct, turnover_pct, amount, volume, big_net_pct, market, source FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100',
}


def safe_execute(c, sql):
    """安全执行 SQL，返回 (columns, rows)"""
    try:
        c.execute(sql)
        cols = [d[0] for d in c.description]
        return cols, c.fetchall()
    except Exception as e:
        print(f'  SQL ERROR: {e}')
        return [], []


def sync():
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
        conn = hive.connect(host=HIVE_HOST, port=10000)
        c = conn.cursor()
        total = 0

        # 1. 静态查询（简单 SELECT + LIMIT，不触发 MapReduce）
        for key, sql in QUERIES.items():
            cols, rows = safe_execute(c, sql)
            if rows:
                rs = [dict(zip(cols, row)) for row in rows]
                r.setex(key, 300, json.dumps(rs, ensure_ascii=False, default=str))
                total += len(rs)

        # 2. K线: 分页读取避免 MR
        cols, rows = safe_execute(c, "SELECT stock_code, trade_date, open, high, low, close, volume, amount, change_pct FROM stock_daily LIMIT 30000")
        if rows:
            rs = [dict(zip(cols, row)) for row in rows]
            # 按 stock_code 分组写入
            by_code = {}
            for rec in rs:
                code = rec["stock_code"]
                if code not in by_code:
                    by_code[code] = []
                by_code[code].append(rec)
            for code, klines in by_code.items():
                r.setex(f"market:kline_{code}", 600, json.dumps(klines, ensure_ascii=False, default=str))
                total += len(klines)
            print(f'  kline: {len(by_code)} stocks, {sum(len(v) for v in by_code.values())} records')

        # 3. 行业排行: 仅在数据量小时执行
        cols2, rows2 = safe_execute(c, "SELECT stock_code, stock_name, ROUND(close, 2) AS last_close, ROUND(volume, 0) AS last_volume, ROUND(change_pct, 2) AS change_p FROM stock_daily LIMIT 5000")
        if rows2:
            rs2 = [dict(zip(cols2, row)) for row in rows2]
            r.setex("market:sector_ranking", 300, json.dumps(rs2, ensure_ascii=False, default=str))
            total += len(rs2)
            print(f'  sector_ranking: {len(rs2)} rows')

        conn.close()
        print(f'[{time.strftime("%H:%M:%S")}] Synced {total} items to Redis')
    except Exception as e:
        print(f'[{time.strftime("%H:%M:%S")}] Sync failed: {e}')


if __name__ == '__main__':
    print('Hive->Redis pipeline started (kline + sectors)')
    while True:
        sync()
        time.sleep(60)
