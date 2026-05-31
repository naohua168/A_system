"""从 Redis 概念板块+stock_daily 生成 sector_kline"""
import sys, json
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

R = redis.Redis(host='redis', port=6379, db=0)
DD = 86400

print('1. Building stock→sector map from Redis concept_blocks...')
ind_map = {}
for k in R.keys('market:concept_blocks_*'):
    try:
        d = json.loads(R.get(k))
        if isinstance(d, list) and d:
            code = d[0].get('stockCode') or d[0].get('stock_code') or d[0].get('conceptCode','')
            if not code or code.startswith('BK'): continue
            sector = d[0].get('conceptName') or d[0].get('blockName') or d[0].get('block_name','')
            if sector and code:
                ind_map[code] = sector
    except: pass
print(f'   {len(ind_map)} stocks with sector info')

if not ind_map:
    print('   No concept data! Using market prefix as sector.')
    # Fallback: use stock_basic to get stock list
    c = hive.connect(host='hive-server', port=10000).cursor()
    c.execute("SELECT stock_code FROM stock_basic")
    for r in c.fetchall():
        code = r[0]
        # Map SH/SZ/BJ as sectors
        if code.startswith(('6','9')): ind_map[code] = '上海主板'
        elif code.startswith(('0','1','2','3')): ind_map[code] = '深圳主板'
        elif code.startswith(('8','4')): ind_map[code] = '北京'
        else: ind_map[code] = '其他'
    print(f'   Fallback: {len(ind_map)} stocks')

print('2. Loading stock_daily from Hive...')
c = hive.connect(host='hive-server', port=10000).cursor()
c.execute("SELECT stock_code, trade_date, close, volume, amount, change_pct FROM stock_daily LIMIT 332520")
daily = c.fetchall()
print(f'   {len(daily)} records')

print('3. Aggregating...')
import collections
sector_dates = collections.defaultdict(lambda: collections.defaultdict(list))
for row in daily:
    code, date, close, vol, amt, chg = row[0], str(row[1]), row[2], row[3], row[4], row[5]
    ind = ind_map.get(code)
    if not ind: continue
    try:
        sector_dates[ind][date].append({
            'close': float(close or 0), 'volume': float(vol or 0),
            'amount': float(amt or 0), 'change_pct': float(chg or 0)
        })
    except: pass

print('4. Computing and writing sector klines...')
count = 0
for sector, dates_data in sector_dates.items():
    klines = []
    for date, stocks in sorted(dates_data.items()):
        if not stocks: continue
        avg_close = sum(s['close'] for s in stocks) / len(stocks)
        avg_vol = sum(s['volume'] for s in stocks)
        total_amt = sum(s['amount'] for s in stocks)
        avg_chg = sum(s['change_pct'] for s in stocks) / len(stocks)
        klines.append({
            'tradeDate': date, 'closePrice': round(avg_close, 2),
            'volume': round(avg_vol, 0), 'amount': round(total_amt, 0),
            'changePercent': round(avg_chg, 2), 'stockCount': len(stocks)
        })
    if klines:
        klines.sort(key=lambda x: x['tradeDate'])
        R.setex(f'market:sector_kline_{sector}', DD,
                json.dumps(klines, ensure_ascii=False, default=str))
        count += 1
        if count % 10 == 0: print(f'   {count} sectors done...', flush=True)

print(f'Done! Generated sector_kline for {count} sectors')
print(f'DBSIZE: {R.dbsize()}')
