"""强制写入所有关键数据的正确 camelCase 版本"""
import json, sys, time
sys.path.insert(0, '/app/pylib')
import redis
from pyhive import hive

R = redis.Redis(host='redis', port=6379, db=0)
DD = 86400; HH = 3600

def hq(s):
    try:
        c = hive.connect(host='hive-server', port=10000).cursor()
        c.execute(s)
        cols = [d[0].split('.')[-1] for d in c.description]
        return [dict(zip(cols, r)) for r in c.fetchall()]
    except:
        return []

# 1. stock_basic — 加上 pe, mcapYi, turnoverPct  
print('1. stock_basic + detail price...')
basic = hq("SELECT stock_code, stock_name, pe_ttm, mcap_yi, turnover_pct FROM stock_basic LIMIT 500")
quote = hq("SELECT stock_code, price, change_pct FROM tencent_quote")
price_map = {r['stock_code']: r for r in quote} if quote else {}
if basic:
    data = []
    for r in basic:
        code = r['stock_code']
        q = price_map.get(code, {})
        data.append({
            'stockCode': code, 'stockName': r['stock_name'],
            'pe': float(r.get('pe_ttm',0) or 0),
            'mcapYi': float(r.get('mcap_yi',0) or 0),
            'turnoverPct': float(r.get('turnover_pct',0) or 0),
            'price': float(q.get('price',0) or 0),
            'changePct': float(q.get('change_pct',0) or 0),
        })
    R.setex('market:stock_basic', HH, json.dumps(data[:200], ensure_ascii=False))
    print(f'  200 items with price, changePct')

# 2. industry_compare — camelCase
print('2. industry_compare...')
ind = hq("SELECT industry, code, change_pct, up_count, down_count FROM industry_compare")
if ind:
    data = [{'industryName':r.get('industry'),'changePct':float(r.get('change_pct',0)or 0),
             'upCount':int(r.get('up_count',0)or 0),'downCount':int(r.get('down_count',0)or 0),
             'stockCode':r.get('code')} for r in ind]
    R.setex('market:industry_compare', HH, json.dumps(data, ensure_ascii=False))
    print(f'  {len(data)} industries')

# 3. sector_ranking — camelCase  
print('3. sector_ranking...')
if basic:
    data2 = [{'stockCode':r['stock_code'],'stockName':r['stock_name'],
              'pe':float(r.get('pe_ttm',0)or 0),'mcapYi':float(r.get('mcap_yi',0)or 0),
              'turnoverPct':float(r.get('turnover_pct',0)or 0) } for r in basic[:200]]
    R.setex('market:sector_ranking', HH, json.dumps(data2, ensure_ascii=False))
    print(f'  200 items')

# 4. northbound — use latest non-zero
print('4. northbound...')
nb = hq("SELECT * FROM signal_northbound LIMIT 50")
if nb:
    # sort by trade_date and take 20
    nb.sort(key=lambda x: str(x.get('trade_date','')), reverse=True)
    data = [{'tradeDate':r['trade_date'],'hgtYi':float(r.get('hgt_yi',0)or 0),
             'sgtYi':float(r.get('sgt_yi',0)or 0)} for r in nb[:20]]
    R.setex('market:northbound', DD, json.dumps(data, ensure_ascii=False))
    print(f'  {len(data)} items, last hgtYi={data[-1]["hgtYi"]}')

# 5. hot_reason — camelCase
print('5. hot_reason...')
hr = hq("SELECT id, name AS stock_name, code AS stock_code, reason, trade_date, change_pct, turnover_pct FROM signal_hot_reason LIMIT 200")
if hr:
    data = [{'id':r.get('id'),'stockCode':r['stock_code'],'stockName':r['stock_name'],
             'reason':r.get('reason'),'tradeDate':r.get('trade_date'),
             'changePct':float(r.get('change_pct',0)or 0),
             'turnoverPct':float(r.get('turnover_pct',0)or 0)} for r in hr]
    R.setex('market:hot_reason', HH, json.dumps(data[:100], ensure_ascii=False))
    print(f'  {len(data)} items')

# 6. dragon_tiger — camelCase with Wan fields
print('6. dragon_tiger...')
dt = hq("SELECT trade_date, stock_code, stock_name, reason, net_buy_wan, buy_wan, sell_wan, change_pct FROM dragon_tiger")
if dt:
    data = [{'tradeDate':r['trade_date'],'stockCode':r['stock_code'],'stockName':r['stock_name'],
             'reason':r.get('reason'),'netBuyWan':float(r.get('net_buy_wan',0)or 0),
             'buyWan':float(r.get('buy_wan',0)or 0),'sellWan':float(r.get('sell_wan',0)or 0),
             'changePct':float(r.get('change_pct',0)or 0)} for r in dt]
    R.setex('market:dragon_tiger', HH, json.dumps(data, ensure_ascii=False))
    print(f'  {len(data)} items')

# 7. cls_news — camelCase  
print('7. cls_news...')
news = hq("SELECT title, content, datetime, source FROM info_cls_news LIMIT 500")
if news:
    data = [{'title':r.get('title'),'content':r.get('content'),
             'publishTime':r.get('datetime'),'source':r.get('source')} for r in news]
    R.setex('market:cls_news', DD, json.dumps(data[:100], ensure_ascii=False))
    print(f'  {len(data)} items')

# 8. global_news — camelCase
print('8. global_news...')
gn = hq("SELECT title, summary, publish_time, url FROM info_global_news LIMIT 200")
if gn:
    data = [{'title':r.get('title'),'summary':r.get('summary'),
             'publishTime':r.get('publish_time'),'url':r.get('url')} for r in gn]
    R.setex('market:global_news', DD, json.dumps(data[:50], ensure_ascii=False))
    print(f'  {len(data)} items')

# 9. fund_list — with all fields
print('9. fund_list...')
funds = hq("SELECT fund_code, fund_name, fund_type, company, manager, scale FROM fund_basic WHERE scale>0 LIMIT 500")
if funds:
    data = [{'fundCode':r['fund_code'],'fundName':r.get('fund_name'),'fundType':r.get('fund_type'),
             'company':r.get('company'),'manager':r.get('manager'),
             'scale':float(r.get('scale',0)or 0)} for r in funds]
    data.sort(key=lambda x: x['scale'], reverse=True)
    R.setex('market:fund_list', DD, json.dumps(data[:200], ensure_ascii=False))
    print(f'  {len(data)} items')

# 10. fund_nav — camelCase
print('10. fund_nav...')
fn = hq("SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav LIMIT 200")
if fn:
    data = [{'fundCode':r['fund_code'],'navDate':r.get('nav_date'),
             'nav':float(r.get('nav',0)or 0),'accumulatedNav':float(r.get('accumulated_nav',0)or 0)} for r in fn]
    R.setex('market:fund_nav', DD, json.dumps(data[:100], ensure_ascii=False))
    print(f'  {len(data)} items')

print(f'\nDone! DBSIZE: {R.dbsize()}')
