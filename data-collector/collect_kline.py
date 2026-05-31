"""
从腾讯财经采集真实K线数据 → Redis
支持指数日K线和个股日K线
使用并发请求加速采集
"""
import sys, json, time, glob, os
sys.path.insert(0, '/app/pylib')

import redis, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

rd = redis.Redis(host='redis', port=6379, db=0)
TTL = 604800  # 7天
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
MAX_WORKERS = 20  # 并发数

def read_stock_list():
    """从CSV读取股票列表"""
    files = sorted(glob.glob('/data/raw/tencent_quote_*.csv'))
    if not files:
        files = sorted(glob.glob('/data/raw/stock_basic_*.csv'))
    if not files:
        print('ERROR: stock_basic CSV not found')
        return []
    stocks = []
    with open(files[-1], 'r', encoding='utf-8-sig') as f:
        import csv
        for row in csv.DictReader(f):
            code = row.get('code', '') or row.get('stock_code', '')
            if code:
                stocks.append(code)
    return stocks

def get_prefix(code, is_index=False):
    """代码前缀：指数和股票规则不同"""
    if is_index:
        # 指数: 000(上证) / 399(深圳) / 688(科创)
        if code.startswith(('0', '6', '9')):
            return 'sh'
        return 'sz'
    # 股票
    if code.startswith(('6', '9')):
        return 'sh'
    elif code.startswith(('0', '1', '2', '3')):
        return 'sz'
    elif code.startswith('8'):
        return 'bj'
    return 'sz'

def fetch_kline(code, is_index=False):
    """从腾讯API获取日K线"""
    prefix = get_prefix(code, is_index)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,120,qfq"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        d = r.json()
    except:
        return None
    data = d.get("data", {})
    # Index: "day", Stock: "qfqday" (前复权日线)
    record = data.get(code) or data.get(prefix + code) or {}
    klines = record.get("qfqday") or record.get("day") or []
    if not klines:
        klines = data.get("qt", {}).get(code, {}).get("day") or data.get("qt", {}).get(code, {}).get("qfqday") or []
    if not klines:
        return None

    rows = []
    for k in klines:
        if len(k) < 6:
            continue
        trade_date = k[0].replace("-", "")
        o, c, h, l = float(k[1]), float(k[2]), float(k[3]), float(k[4])
        v = int(float(k[5])) if len(k) > 5 else 0
        a = float(k[6]) if len(k) > 6 else 0
        change_pct = round((c - o) / o * 100, 2) if o > 0 else 0

        if is_index:
            row = {
                'index_code': code,
                'trade_date': trade_date,
                'open_point': o,
                'close_point': c,
                'high_point': h,
                'low_point': l,
                'volume': v,
                'amount': a,
                'change_pct': change_pct,
            }
        else:
            # Stock kline - use *Price suffix
            row = {
                'stock_code': code,
                'trade_date': trade_date,
                'open_price': o,
                'close_price': c,
                'high_price': h,
                'low_price': l,
                'volume': v,
                'amount': a,
                'change_pct': change_pct,
                'pre_close': o,  # approximate: use open as preClose
                'turnover_rate': 0,
            }
        rows.append(row)
    return rows

def write_to_redis(code, klines, is_index=False):
    """写入Redis"""
    if not klines:
        return 0
    key = f'market:index_kline_{code}' if is_index else f'market:kline_{code}'
    # Field name mapping: snake_case → camelCase
    import re
    def to_camel(s):
        parts = s.split('_')
        return parts[0] + ''.join(p.capitalize() for p in parts[1:])

    camel_klines = []
    for row in klines:
        camel_row = {to_camel(k): v for k, v in row.items()}
        # Special overrides for specific field names
        camel_row['changePct'] = camel_row.pop('changePct', 0)
        camel_row['preClose'] = camel_row.get('preClose', 0)
        if is_index:
            pass  # fields already correct: openPoint, closePoint etc.
        else:
            # Stock: openPoint→openPrice is handled by to_camel correctly
            # 'open_point'→'openPoint' but we need 'openPrice'
            # We stored as 'open_price' which to_camel converts to 'openPrice' ✓
            pass
        camel_klines.append(camel_row)

    # 降序存储（最新在前），前端期望 DESC
    camel_klines.reverse()
    rd.setex(key, TTL, json.dumps(camel_klines, ensure_ascii=False, default=str))
    return len(camel_klines)

def collect_indices():
    """采集5个指数的K线"""
    indices = ['000001', '399001', '399006', '000688', '000300']
    count = 0
    print(f'[{datetime.now():%H:%M:%S}] 采集指数K线...')
    for code in indices:
        klines = fetch_kline(code, is_index=True)
        if klines:
            n = write_to_redis(code, klines, is_index=True)
            print(f'  指数 {code}: {n}条K线')
            count += n
        else:
            print(f'  指数 {code}: 采集失败')
        time.sleep(0.3)  # 限流
    return count

def collect_one_stock(code):
    """采集单只股票K线"""
    klines = fetch_kline(code, is_index=False)
    if klines:
        n = write_to_redis(code, klines, is_index=False)
        return code, n
    return code, 0

def collect_stocks():
    """采集所有股票的K线（并发）"""
    stock_codes = read_stock_list()
    print(f'[{datetime.now():%H:%M:%S}] 从CSV读取 {len(stock_codes)} 只股票')
    total = 0
    success = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(collect_one_stock, code): code for code in stock_codes}
        done = 0
        for future in as_completed(futures):
            code, n = future.result()
            done += 1
            if n > 0:
                total += n
                success += 1
            if done % 100 == 0:
                print(f'  [{datetime.now():%H:%M:%S}] 进度: {done}/{len(stock_codes)}, 成功: {success}, K线条数: {total}')
    return total, success

if __name__ == '__main__':
    t0 = time.time()
    print(f'=== K线数据采集启动 [{datetime.now():%H:%M:%S}] ===')

    # 1. 采集指数K线
    idx_count = collect_indices()
    print(f'\n✅ 指数K线: {idx_count}条')

    # 2. 采集个股K线
    stock_total, stock_ok = collect_stocks()
    elapsed = time.time() - t0
    print(f'\n{"="*50}')
    print(f'✅ 个股K线: {stock_total}条, 成功{stock_ok}只')
    print(f'⏱ 耗时: {elapsed:.0f}s, Redis DBSIZE: {rd.dbsize()}')
    print(f'{"="*50}')
