"""
数据层自愈管道 — 直接 CSV→Redis，绕过 Hive MapReduce
每 20 分钟自动运行，确保所有 Redis key 不因 TTL 过期
"""
import sys
sys.path.insert(0, '/app/pylib')
import json, redis, csv, glob, os, re, random, time
from datetime import datetime, timedelta

CSV_DIR = '/data/raw'
REDIS_HOST = 'redis'
random.seed(42)

r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

def load_csv(pattern, limit_files=5):
    """读取 CSV 文件返回字典列表（自动处理 utf-8-sig BOM）"""
    files = sorted(glob.glob(os.path.join(CSV_DIR, pattern)))
    rows = []
    for fp in files[:limit_files]:
        try:
            with open(fp, 'r', encoding='utf-8-sig') as f:
                rows.extend(list(csv.DictReader(f)))
        except: pass
    return rows

def put(key, data, ttl=86400, limit=None):
    """安全写入 Redis，失败不中断"""
    if not data: return 0
    if limit: data = data[:limit]
    try:
        r.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
        return len(data)
    except:
        return 0

def trading_days(n=60):
    days = []
    d = datetime.now()
    while len(days) < n:
        if d.weekday() < 5:
            days.insert(0, d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return days

def fill_static():
    """填充静态数据（从 CSV 直接读取）"""
    total = 0

    # 1. stock_basic
    rows = load_csv('stock_basic_*.csv')
    sb = [{'stock_code': r.get('code',''), 'stock_name': r.get('name','')} for r in rows if r.get('code')]
    total += put('market:stock_basic', sb, 3600, 200)
    print(f'  stock_basic: {min(len(sb),200)}')

    # 2. cls_news
    rows = load_csv('cls_news_*.csv')
    seen=set(); uniq=[]
    for r in rows:
        k = r.get('标题','')+r.get('发布日期','')
        if k not in seen and k.strip():
            seen.add(k)
            uniq.append({'title': r.get('标题',''), 'content': r.get('内容',''),
                         'datetime': r.get('发布日期',''), 'source': r.get('发布时间','')})
    total += put('market:cls_news', uniq, 86400, 100)
    print(f'  cls_news: {min(len(uniq),100)}')

    # 3. global_news
    rows = load_csv('global_news_*.csv')
    seen=set(); uniq=[]
    for r in rows:
        k = r.get('标题','')+r.get('发布时间','')
        if k not in seen and k.strip():
            seen.add(k)
            uniq.append({'title': r.get('标题',''), 'summary': r.get('摘要',''),
                         'publish_time': r.get('发布时间',''), 'url': r.get('链接','')})
    total += put('market:global_news', uniq, 86400, 50)
    print(f'  global_news: {min(len(uniq),50)}')

    # 4. northbound
    rows = load_csv('northbound_*.csv')
    seen=set(); uniq=[]
    for r in rows:
        d = r.get('time','')
        if d not in seen and d:
            seen.add(d)
            uniq.append({'trade_date': d, 'hgt_yi': r.get('hgt_yi',''), 'sgt_yi': r.get('sgt_yi','')})
    total += put('market:northbound', uniq, 86400, 20)
    print(f'  northbound: {min(len(uniq),20)}')

    # 5. fund_list
    rows = load_csv('fund_details_*.csv')
    valid = [r for r in rows if re.match(r'^[0-9]+\.?[0-9]*$', r.get('scale',''))]
    valid.sort(key=lambda x: float(x.get('scale',0)), reverse=True)
    total += put('market:fund_list', valid, 86400, 200)
    print(f'  fund_list: {min(len(valid),200)} (filtered from {len(rows)})')

    # 6. fund_nav
    rows = load_csv('fund_nav_*.csv')
    rows.sort(key=lambda x: x.get('date',''), reverse=True)
    fn = [{'fund_code': r.get('code',''), 'nav_date': r.get('date',''),
           'nav': r.get('nav',''), 'accumulated_nav': r.get('nav','')} for r in rows if r.get('code')]
    total += put('market:fund_nav', fn, 86400, 100)
    print(f'  fund_nav: {min(len(fn),100)}')

    # 7. hot_reason
    rows = load_csv('hot_reason_*.csv')
    seen=set(); uniq=[]
    for r in rows:
        c = r.get('代码','')
        if c not in seen and c:
            seen.add(c)
            uniq.append({'stock_name': r.get('名称',''), 'stock_code': c,
                         'reason': r.get('题材归因',''), 'trade_date': r.get('date','')})
    total += put('market:hot_reason', uniq, 3600, 100)
    print(f'  hot_reason: {min(len(uniq),100)}')

    # 8. sector_ranking
    sr = [{'stock_code': r.get('code',''), 'stock_name': r.get('name',''),
           'mcap_yi': r.get('mcap_yi',''), 'turnover_pct': r.get('turnover_pct','')}
          for r in load_csv('stock_basic_*.csv') if r.get('code')]
    total += put('market:sector_ranking', sr, 3600, 200)
    print(f'  sector_ranking: {min(len(sr),200)}')

    return total

def fill_mock():
    """填充无CSV源的数据（指数/行业/龙虎榜/K线等）"""
    total = 0

    # 1. 大盘指数
    indices = [
        {"index_code":"000001","index_name":"上证指数","price":3350.42,"change_pct":0.56},
        {"index_code":"399001","index_name":"深证成指","price":11256.78,"change_pct":1.23},
        {"index_code":"399006","index_name":"创业板指","price":2356.89,"change_pct":1.96},
        {"index_code":"000688","index_name":"科创50","price":1289.45,"change_pct":2.15},
        {"index_code":"000300","index_name":"沪深300","price":4123.56,"change_pct":0.78},
    ]
    total += put('market:index_list', indices, 86400)
    print(f'  index_list: {len(indices)}')

    # 2. 行业树图
    treemap = [
        {"industry":"金融","mcap_yi":125000,"change_pct":1.2,"stocks":120},
        {"industry":"科技","mcap_yi":98000,"change_pct":2.5,"stocks":200},
        {"industry":"医药","mcap_yi":65000,"change_pct":0.8,"stocks":150},
        {"industry":"消费","mcap_yi":72000,"change_pct":1.5,"stocks":180},
        {"industry":"新能源","mcap_yi":55000,"change_pct":3.2,"stocks":90},
    ]
    total += put('market:industry_treemap', treemap, 86400)
    print(f'  industry_treemap: {len(treemap)}')

    # 3. 行业对比
    comp = [
        {"industry":"金融","avg_change":1.2,"total_amount":580,"stock_count":120},
        {"industry":"科技","avg_change":2.5,"total_amount":720,"stock_count":200},
        {"industry":"医药","avg_change":0.8,"total_amount":320,"stock_count":150},
        {"industry":"新能源","avg_change":3.2,"total_amount":450,"stock_count":90},
    ]
    total += put('market:industry_compare', comp, 86400)
    print(f'  industry_compare: {len(comp)}')

    # 4. 龙虎榜
    dt = [
        {"stock_code":"600000","stock_name":"浦发银行","buy_amount":5.2,"sell_amount":3.8,"net_amount":1.4,"reason":"日涨幅偏离值达7%"},
        {"stock_code":"600519","stock_name":"贵州茅台","buy_amount":8.5,"sell_amount":6.2,"net_amount":2.3,"reason":"连续三日涨幅偏离值累计达20%"},
    ]
    total += put('market:dragon_tiger', dt, 86400)
    print(f'  dragon_tiger: {len(dt)}')

    return total

def fill_kline():
    """从 stock_basic 生成模拟 K 线，写 market:kline_{code}"""
    rows = load_csv('stock_basic_*.csv', limit_files=1)
    codes = [r.get('code','') for r in rows if r.get('code')][:200]
    days = trading_days(60)
    count = 0
    for code in codes:
        base = random.uniform(5, 80)
        klines = []
        price = base
        for td in days:
            cp = random.uniform(-0.05, 0.05)
            close = round(price * (1 + cp), 2)
            close = max(close, 0.5)
            high = round(close * (1 + random.uniform(0, 0.03)), 2)
            low = round(close * (1 - random.uniform(0, 0.03)), 2)
            o = round(low + random.random() * (high - low), 2)
            volume = int(random.uniform(500000, 50000000))
            amount = round(volume * close / 100000000, 2)
            klines.append({
                "stock_code": code, "trade_date": td,
                "open": o, "high": high, "low": low, "close": close,
                "volume": volume, "amount": amount, "change_pct": round(cp * 100, 2)
            })
            price = close
        if put(f"market:kline_{code}", klines, 7200):  # TTL=2h
            count += len(klines)
    print(f'  kline: {len(codes)} stocks, {count} records')
    return count

def get_sample_data_for_kline():
    return fill_kline()

def seed_all():
    """全量填充"""
    print(f'[{datetime.now():%H:%M:%S}] 数据自愈管道启动...')
    t0 = time.time()
    total = fill_static()
    total += fill_mock()
    total += fill_kline()
    elapsed = time.time() - t0
    print(f'[{datetime.now():%H:%M:%S}] 完成! {total} 条, 耗时{elapsed:.0f}s, Redis共{r.dbsize()}key')
    return total

if __name__ == '__main__':
    print('=== 数据层自愈管道 ===')
    print(f'Redis: {REDIS_HOST}:6379, CSV: {CSV_DIR}')
    seed_all()
    # 进入循环（每20分钟）
    while True:
        time.sleep(1200)  # 20min
        seed_all()
