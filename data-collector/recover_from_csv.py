"""从全量 CSV 恢复 Redis 数据（5,543 只股票，真实数据）"""
import json, csv, sys, glob, os
sys.path.insert(0, '/app/pylib')
import redis
from datetime import datetime
from collections import defaultdict

r = redis.Redis(host='redis', port=6379, db=0)
CSV_DIR = '/data/raw'

def load_csv(name, limit_files=1):
    pattern1 = os.path.join(CSV_DIR, name + '_*.csv')
    pattern2 = os.path.join(CSV_DIR, name + '.csv')
    files = sorted(glob.glob(pattern1) + glob.glob(pattern2))
    rows = []
    for fp in files[-limit_files:]:
        try:
            with open(fp, 'r', encoding='utf-8-sig') as f:
                rows.extend(list(csv.DictReader(f)))
        except Exception as e:
            print('  load error', name, e)
    return rows

all_csv = glob.glob(os.path.join(CSV_DIR, '*.csv'))
print(f'[{datetime.now():%H:%M:%S}] 全量数据恢复启动, CSV: {len(all_csv)} files')

# 1. tencent_quote -> detail + stock_basic
tq = load_csv('tencent_quote')
print(f'1. tencent_quote: {len(tq)} rows')

detail_count = 0
sb_list = []
for row in tq:
    code = row.get('stock_code') or row.get('code') or ''
    name = row.get('stock_name') or row.get('name') or ''
    if not code: continue
    item = {
        'stockCode': code, 'stockName': name,
        'price': float(row.get('price') or 0),
        'changePercent': float(row.get('change_pct') or 0),
        'mcapYi': float(row.get('mcap_yi') or 0),
        'turnoverPct': float(row.get('turnover_pct') or 0),
        'pe': float(row.get('pe_ttm') or 0),
        'pb': float(row.get('pb') or 0),
        'openPrice': float(row.get('open') or 0),
        'highPrice': float(row.get('high') or 0),
        'lowPrice': float(row.get('low') or 0),
        'closePoint': float(row.get('price') or 0),
        'volume': float(row.get('volume') or 0),
        'amount': float(row.get('amount') or 0),
        'industryName': row.get('industry') or '',
    }
    r.setex(f'market:detail_{code}', 86400, json.dumps(item, ensure_ascii=False, default=str))
    detail_count += 1
    sb_list.append({
        'stockCode': code, 'stockName': name,
        'price': item['price'], 'changePercent': item['changePercent'],
        'mcapYi': item['mcapYi'], 'pe': item['pe'],
        'turnoverPct': item['turnoverPct'],
    })
print(f'  detail: {detail_count}, stock_basic: {len(sb_list)}')

r.setex('market:stock_basic', 3600, json.dumps(sb_list, ensure_ascii=False, default=str))

# 2. fund_flow
ff = load_csv('fund_flow')
if ff:
    flow_by = defaultdict(list)
    for row in ff:
        code = row.get('stock_code') or row.get('code') or ''
        if code:
            flow_by[code].append({
                'stockCode': code, 'tradeDate': row.get('trade_date',''),
                'mainIn': float(row.get('main_net') or 0),
                'superNetIn': float(row.get('super_net') or 0),
                'largeNetIn': float(row.get('large_net') or 0),
                'mediumNetIn': float(row.get('mid_net') or 0),
                'littleNetIn': float(row.get('small_net') or 0),
            })
    for code, items in flow_by.items():
        r.setex(f'market:fund_flow_{code}', 7200, json.dumps(items, ensure_ascii=False, default=str))
    print(f'2. fund_flow: {len(flow_by)} stocks')

# 3. lockup
lk = load_csv('lockup')
if lk:
    lu_by = defaultdict(list)
    for row in lk:
        code = row.get('stock_code') or row.get('code') or ''
        if code:
            lu_by[code].append({
                'stockCode': code, 'lockupDate': row.get('free_date') or row.get('lockup_date') or '',
                'lockupType': row.get('lockup_type') or '',
                'floatRatio': float(row.get('ratio') or 0),
                'shares': float(row.get('shares') or row.get('share') or 0),
            })
    for code, items in lu_by.items():
        r.setex(f'market:lockup_{code}', 86400, json.dumps(items, ensure_ascii=False, default=str))
    upc = [it for its in lu_by.values() for it in its]
    r.setex('market:lockup_upcoming', 86400, json.dumps(upc[:50], ensure_ascii=False, default=str))
    print(f'3. lockup: {len(lu_by)} stocks')

# 4. industry_compare
ic = load_csv('industry_compare')
if ic:
    ind_comp = [{'industryName': r.get('industry') or r.get('industry_name') or '',
                 'changePct': float(r.get('avg_change') or r.get('change_pct') or 0),
                 'stockCount': int(r.get('stock_count') or 0),
                 'totalAmount': float(r.get('total_amount') or 0)} for r in ic]
    r.setex('market:industry_compare', 86400, json.dumps(ind_comp, ensure_ascii=False, default=str))
    treemap = [{'industryName': x['industryName'], 'changePercent': x['changePct'],
                'mcapYi': x['totalAmount'], 'stocks': x['stockCount']} for x in ind_comp]
    r.setex('market:industry_treemap', 86400, json.dumps(treemap, ensure_ascii=False, default=str))
    print(f'4. industry_compare: {len(ind_comp)}')

# 5. stock_news
sn = load_csv('stock_news')
if sn:
    news_by = defaultdict(list)
    for row in sn:
        code = row.get('stock_code') or row.get('code') or ''
        if code:
            news_by[code].append({
                'stockCode': code, 'title': row.get('title',''),
                'publishTime': row.get('publish_time') or row.get('datetime') or '',
                'content': row.get('content',''),
            })
    for code, items in news_by.items():
        r.setex(f'market:news_{code}', 86400, json.dumps(items[:20], ensure_ascii=False, default=str))
    print(f'5. stock_news: {len(news_by)} stocks')

# 6. filings
fl = load_csv('filings')
if fl:
    fl_by = defaultdict(list)
    for row in fl:
        code = row.get('stock_code') or row.get('code') or ''
        if code:
            fl_by[code].append({
                'stockCode': code, 'title': row.get('title',''),
                'publishDate': row.get('publish_date') or row.get('datetime') or '',
                'filingType': row.get('type') or '',
            })
    for code, items in fl_by.items():
        r.setex(f'market:filings_{code}', 86400, json.dumps(items[:20], ensure_ascii=False, default=str))
    print(f'6. filings: {len(fl_by)} stocks')

# 7. northbound
nb = load_csv('northbound', 7)
if nb:
    nb_list = [{'tradeDate': r.get('trade_date',''), 'hgtYi': float(r.get('hgt_yi') or 0),
                'sgtYi': float(r.get('sgt_yi') or 0)} for r in nb]
    r.setex('market:northbound', 86400, json.dumps(nb_list, ensure_ascii=False, default=str))
    print(f'7. northbound: {len(nb_list)}')

# 8. hot_reason
hr = load_csv('hot_reason')
if hr:
    hr_list = [{'stockCode': r.get('code',''), 'stockName': r.get('name',''),
                'reason': r.get('reason',''), 'tradeDate': r.get('trade_date','')} for r in hr]
    r.setex('market:hot_reason', 3600, json.dumps(hr_list, ensure_ascii=False, default=str))
    print(f'8. hot_reason: {len(hr_list)}')

# 9. tencent_index
ti = load_csv('tencent_index')
if ti:
    idx_list = [{'indexCode': r.get('index_code',''), 'indexName': r.get('index_name',''),
                 'closePoint': float(r.get('price') or 0),
                 'changePercent': float(r.get('change_pct') or 0)} for r in ti]
    r.setex('market:index_list', 3600, json.dumps(idx_list, ensure_ascii=False, default=str))
    print(f'9. index_list: {len(idx_list)}')

# 10. fund_basic / fund_nav
fb = load_csv('fund_basic')
if fb:
    flist = [{'fundCode': r.get('fund_code',''), 'fundName': r.get('fund_name',''),
              'fundType': r.get('fund_type',''), 'company': r.get('company',''),
              'scale': float(r.get('scale') or 0)} for r in fb if float(r.get('scale') or 0) > 0]
    r.setex('market:fund_list', 86400, json.dumps(flist[:500], ensure_ascii=False, default=str))
    print(f'10. fund_list: {len(flist)}')

fn = load_csv('fund_nav')
if fn:
    fnav = [{'fundCode': r.get('fund_code',''), 'navDate': r.get('nav_date',''),
             'nav': float(r.get('nav') or 0)} for r in fn]
    r.setex('market:fund_nav', 86400, json.dumps(fnav[:100], ensure_ascii=False, default=str))
    print(f'   fund_nav: {len(fnav)}')

# 11. cls_news / global_news
cn = load_csv('cls_news')
if cn:
    cn_list = [{'title': r.get('title',''), 'content': r.get('content',''),
                'publishTime': r.get('datetime',''), 'source': r.get('source','')} for r in cn]
    r.setex('market:cls_news', 3600, json.dumps(cn_list[:100], ensure_ascii=False, default=str))
    print(f'11. cls_news: {len(cn_list)}')

gn = load_csv('global_news')
if gn:
    gn_list = [{'title': r.get('title',''), 'summary': r.get('summary',''),
                'publishTime': r.get('publish_time',''), 'url': r.get('url','')} for r in gn]
    r.setex('market:global_news', 3600, json.dumps(gn_list[:50], ensure_ascii=False, default=str))
    print(f'   global_news: {len(gn_list)}')

# 12. industries
inds = sorted(set(row.get('industry', '') for row in tq if row.get('industry')))
if inds:
    r.setex('market:industries', 86400, json.dumps(inds, ensure_ascii=False))
    print(f'12. industries: {len(inds)}')
r.setex('market:market_list', 86400, json.dumps(['sh', 'sz'], ensure_ascii=False))
r.setex('market:max_date', 86400, json.dumps([{'tradeDate': '20260530'}], ensure_ascii=False))

# 13. sector_ranking
r.setex('market:sector_ranking', 3600, json.dumps(sb_list[:200], ensure_ascii=False, default=str))
print(f'13. sector_ranking: {min(200,len(sb_list))}')

# 14. dragon_tiger - deleted (no real source)
r.delete('market:dragon_tiger')
print(f'14. dragon_tiger: DELETED')

print(f'[{datetime.now():%H:%M:%S}] 完成! DBSIZE: {r.dbsize()}')
