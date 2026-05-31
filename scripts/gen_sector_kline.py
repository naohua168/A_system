"""从 stock_daily 生成 sector_kline 数据（Python 聚合避免 MR）"""
import sys, json, time
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

R = redis.Redis(host='redis', port=6379, db=0)

# 1. 加载所有行业映射 (从 concept_blocks 提取 stock→block 映射)
print('1. Loading stock→industry mapping...')
c = hive.connect(host='hive-server', port=10000).cursor()
c.execute("SELECT stock_code, block_name FROM concept_blocks")
raw = c.fetchall()
ind_map = {}
for code, block in raw:
    if code and block:
        ind_map.setdefault(code, block)  # first block = primary industry
print(f'   {len(ind_map)} stocks mapped to industries')

# 2. 加载所有 stock_daily 数据
print('2. Loading stock_daily...')
c.execute("SELECT stock_code, trade_date, close, volume, amount, change_pct FROM stock_daily LIMIT 332520")
daily = c.fetchall()
print(f'   {len(daily)} records loaded')

# 3. 按 trade_date + industry 聚合
print('3. Aggregating...')
import collections
sector_dates = collections.defaultdict(lambda: collections.defaultdict(list))

for row in daily:
    code, date, close, vol, amt, chg = row[0], row[1], row[2], row[3], row[4], row[5]
    ind = ind_map.get(code)
    if not ind:
        continue
    try:
        sector_dates[ind][date].append({
            'close': float(close or 0), 'volume': float(vol or 0),
            'amount': float(amt or 0), 'change_pct': float(chg or 0)
        })
    except:
        pass

# 4. 计算每日行业均值
print('4. Computing sector klines...')
count = 0
for industry, dates_data in sector_dates.items():
    klines = []
    for date, stocks in sorted(dates_data.items()):
        if not stocks:
            continue
        avg_close = sum(s['close'] for s in stocks) / len(stocks)
        avg_vol = sum(s['volume'] for s in stocks) / len(stocks)
        total_amt = sum(s['amount'] for s in stocks)
        avg_chg = sum(s['change_pct'] for s in stocks) / len(stocks)
        klines.append({
            'tradeDate': date, 'closePrice': round(avg_close, 2),
            'volume': round(avg_vol, 0), 'amount': round(total_amt, 0),
            'changePercent': round(avg_chg, 2),
            'stockCount': len(stocks)
        })
    if klines:
        klines.sort(key=lambda x: x['tradeDate'])
        R.setex(f'market:sector_kline_{industry}', 86400,
                json.dumps(klines, ensure_ascii=False, default=str))
        count += 1

print(f'   Generated sector_kline for {count} industries')
print(f'   DBSIZE now: {R.dbsize()}')
