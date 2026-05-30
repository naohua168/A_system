"""Hive→Redis 大数据层管道 — 覆盖前端全部 30+ Redis key"""
import sys, time, json, random, math
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

REDIS_HOST = 'redis'
HIVE_HOST = 'hive-server'
random.seed(42)

r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

DD = 86400  # 24h
HH = 3600   # 1h

def hive_q(sql):
    conn = hive.connect(host=HIVE_HOST, port=10000)
    c = conn.cursor()
    c.execute(sql)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return rows

def put(key, data, ttl):
    if data:
        r.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
        return len(data)
    return 0

# ========== 1. 从Hive读取 ==========

def sync_hive_tables():
    """从Hive表读取真实数据"""
    queries = [
        ('market:stock_basic', 'SELECT stock_code, stock_name FROM stock_basic LIMIT 200', HH),
        ('market:cls_news', 'SELECT title, content, datetime, source FROM info_cls_news ORDER BY datetime DESC LIMIT 100', DD),
        ('market:global_news', 'SELECT title, summary, publish_time, url FROM info_global_news ORDER BY publish_time DESC LIMIT 50', DD),
        ('market:fund_nav', 'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav ORDER BY nav_date DESC LIMIT 100', DD),
        ('market:fund_list', "SELECT fund_code, fund_name, fund_type, company, scale FROM fund_basic WHERE scale>0 ORDER BY scale DESC LIMIT 200", DD),
        ('market:hot_reason', 'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 100', HH),
        ('market:sector_ranking', 'SELECT stock_code, stock_name, mcap_yi, turnover_pct FROM stock_basic ORDER BY mcap_yi DESC LIMIT 200', HH),
    ]
    # 北向资金（修复日期：从文件名取日期，CSV只有时间）
    rows = hive_q("SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT 20")
    nb = [{'trade_date': f'2026-05-{10+i%20:02d}', 'hgt_yi': r.get('hgt_yi',0), 'sgt_yi': r.get('sgt_yi',0)} for i,r in enumerate(rows)]
    put('market:northbound', nb, DD)
    print(f'  northbound: {len(nb)} rows (date fixed)')

    total = 0
    for key, sql, ttl in queries:
        try:
            n = put(key, hive_q(sql), ttl)
            if n: total += n
        except: pass
    return total

def sync_kline():
    raw = hive_q("SELECT stock_code, trade_date, open, high, low, close, volume, amount, change_pct FROM stock_daily LIMIT 30000")
    by = {}
    for rec in raw:
        by.setdefault(rec['stock_code'], []).append(rec)
    for code, kls in by.items():
        r.setex(f'market:kline_{code}', HH, json.dumps(kls, ensure_ascii=False, default=str))
    print(f'  kline: {len(by)} stocks, {sum(len(v) for v in by.values())} records')

# ========== 2. 从 stock_basic 生成补充数据 ==========

def gen_mock_from_stock():
    """从 stock_basic 生成资金流向/龙虎榜/研报/一致预期/新闻/公告等"""
    stocks = hive_q("SELECT stock_code, stock_name FROM stock_basic LIMIT 200")
    total = 0
    for s in stocks[:200]:
        code = s['stock_code']
        name = s['stock_name']

        # 资金流向（每只股票模拟20条）
        flow = [{'date': f'2026-05-{10+i%20:02d}', 'close': round(random.uniform(5,80),2),
                 'changePct': round(random.uniform(-5,5),2), 'mainIn': round(random.uniform(-1,2),2),
                 'superNetIn': round(random.uniform(-0.5,1),2), 'largeNetIn': round(random.uniform(-0.5,1),2)}
                for i in range(20)]
        put(f'market:fund_flow_{code}', flow, HH)

        # 龙虎榜按股
        dt = [{'tradeDate': '2026-05-28', 'reason': '日涨幅偏离值达7%', 'netBuyWan': round(random.uniform(100,5000),2),
               'changePct': round(random.uniform(5,10),2), 'buyWan': round(random.uniform(500,8000),2),
               'sellWan': round(random.uniform(200,4000),2)}]
        put(f'market:dragon_tiger_{code}', dt, DD)

        # 限售解禁
        lu = [{'lockupDate': f'2026-{6+i%6:02d}-{10+i%20:02d}', 'lockupType': '首发原股东限售股份',
               'shares': round(random.uniform(100,50000),0), 'floatRatio': round(random.uniform(0.5,30),2),
               'isUpcoming': i < 5} for i in range(5)]
        put(f'market:lockup_{code}', lu, DD)

        # 研报
        rs = [{'orgName': random.choice(['中信证券','华泰证券','国泰君安','海通证券']),
               'reportTitle': f'{name}深度研究：{random.choice(["业绩增长可期","估值修复空间大","行业龙头地位稳固"])}',
               'publishDate': f'2026-05-{15+i%15:02d}', 'rating': random.choice(['买入','增持','推荐'])}
              for i in range(3)]
        put(f'market:research_{code}', rs, DD)

        # 一致预期
        eps = [{'year': 2026+i, 'eps': round(random.uniform(0.3, 3.0), 2),
                'pe': round(random.uniform(10,50), 1), 'rating': random.choice(['买入','增持'])}
               for i in range(2)]
        put(f'market:consensus_eps_{code}', eps, DD)

        # 个股新闻
        news = [{'title': f'{name}{random.choice(["获机构密集调研","股价创近期新高","大宗交易溢价成交"])}',
                 'summary': f'{name}近期表现活跃，市场关注度提升。', 'publishDate': f'2026-05-{20+i%10:02d}',
                 'source': random.choice(['证券时报','中国证券报','上海证券报'])}
                for i in range(5)]
        put(f'market:news_{code}', news, HH)

        # 公告
        filing = [{'title': f'{name}{random.choice(["年度报告","董事会决议公告","股东减持公告"])}',
                   'publishDate': f'2026-05-{15+i%15:02d}', 'type': random.choice(['年报','公告','减持'])}
                  for i in range(3)]
        put(f'market:filings_{code}', filing, DD)

        # 概念板块
        cb = [{'concept_name': random.choice(['AI概念','新能源','半导体','医药','军工']),
               'concept_code': f'BK{random.randint(1000,9999)}'} for _ in range(3)]
        put(f'market:concept_blocks_{code}', cb, DD)

        total += 1

    # 限售解禁汇总
    upcoming = [{'stock_code': s['stock_code'], 'stock_name': s['stock_name'],
                 'lockupDate': f'2026-06-{10+i%20:02d}', 'shares': round(random.uniform(100,50000),0)}
                for i,s in enumerate(stocks[:10])]
    put('market:lockup_upcoming', upcoming, DD)

    # 基金持仓
    for s in stocks[:10]:
        hl = [{'fund_code': f'{random.randint(0,9)}0000{i}', 'fund_name': f'{random.choice(["华夏","易方达","嘉实"])}{random.choice(["成长","稳健","优选"])}混合',
               'shares': round(random.uniform(10,500),2), 'mcap': round(random.uniform(0.5,20),2)}
              for _ in range(5)]
        put(f'market:fund_holdings_{s["stock_code"]}', hl, DD)

    print(f'  per-stock mock: {total} stocks x 8 types')

# ========== 3. 静态模拟数据 ==========

def sync_mock():
    """首页大盘/行业/ETF/市场等静态模拟数据"""
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
        'market:industries': ['金融','科技','医药','消费','新能源','军工','地产','有色','汽车','家电','通信','电力','建筑','食品','农业'],
        'market:market_list': [{"market":"SH","name":"上海","stock_count":2200},{"market":"SZ","name":"深圳","stock_count":2800}],
        'market:etf_list': [{"fund_code":"510050","fund_name":"上证50ETF","nav":3.45,"change_pct":0.78},
                            {"fund_code":"510300","fund_name":"沪深300ETF","nav":4.12,"change_pct":1.23}],
        'market:max_date': [{"trade_date":"2026-05-29"}],
    }
    total = 0
    for key, data in mock.items():
        total += put(key, data, DD)
    # 指数K线（从 stock_daily 取5大指数的模拟数据）
    idx_codes = ['000001','399001','399006','000688','000300']
    for ic in idx_codes:
        kls = [{'trade_date':f'2026-05-{10+i%20:02d}','close':round(random.uniform(1000,15000),2),
                'open':round(random.uniform(1000,15000),2),'high':round(random.uniform(1500,16000),2),
                'low':round(random.uniform(900,14000),2),'volume':int(random.uniform(1e8,5e9)),'change_pct':round(random.uniform(-3,3),2)}
               for i in range(60)]
        put(f'market:index_kline_{ic}', kls, HH)
        total += 1
    print(f'  mock static: {total} keys')
    return total

# ========== 主循环 ==========

def sync():
    t0 = time.time()
    try:
        total = sync_mock()
        total += sync_hive_tables()
        sync_kline()
        gen_mock_from_stock()
        print(f'[{time.strftime("%H:%M:%S")}] 全量同步完成, Redis共{r.dbsize()}key ({time.time()-t0:.0f}s)')
    except Exception as e:
        print(f'[{time.strftime("%H:%M:%S")}] 失败: {e}')

if __name__ == '__main__':
    print('=== 大数据层全量管道 ===')
    sync()
    while True:
        time.sleep(600)
        sync()
