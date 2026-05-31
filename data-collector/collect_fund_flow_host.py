"""
宿主机运行：从东方财富采集资金流向数据 → 写入 Docker Redis
使用本地网络（可绕过容器防火墙）
"""
import json, time, csv, glob, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import redis

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TTL = 604800  # 7天
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
MAX_WORKERS = 10
DELAY = 0.05  # 反爬间隔

rd = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# 从本地CSV或容器CSV读取股票列表
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
codes = []
csv_path = os.path.join(SCRIPT_DIR, 'tencent_quote_latest.csv')
csv_glob = sorted(glob.glob(os.path.join(SCRIPT_DIR, 'tencent_quote_*.csv')))
if csv_glob:
    csv_path = csv_glob[-1]
try:
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            c = row.get('stock_code', '') or row.get('code', '')
            if c: codes.append(c)
    print(f'从CSV读取 {len(codes)} 只股票: {csv_path}')
except:
    # Fallback: 生成常见股票代码范围
    print('CSV not found, generating stock codes...')
    # 沪市主板: 600000~605999, 688000~689999
    for prefix in ['600', '601', '603', '605', '688']:
        for i in range(0, 1000):
            codes.append(f'{prefix}{i:03d}')
    # 深市: 000001~003999, 002000~002999, 300000~301999
    for prefix in ['000', '001', '002', '003', '300', '301']:
        for i in range(0, 1000):
            codes.append(f'{prefix}{i:03d}')
    codes = sorted(set(codes))
    print(f'Generated {len(codes)} candidate codes')

def fetch_one(code):
    """采集单只股票资金流向"""
    mk = '1' if code.startswith('6') or code.startswith('9') else '0'
    if code.startswith('8'):
        mk = '0'  # 北交所
    try:
        r = requests.get(
            'https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get',
            params={
                'secid': f'{mk}.{code}',
                'fields1': 'f1,f2,f3,f7',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57',
                'lmt': '120',
            },
            headers={'User-Agent': UA, 'Referer': 'https://quote.eastmoney.com/'},
            timeout=10
        )
        if r.status_code != 200:
            return code, 0
        d = r.json()
        klines = (d.get('data') or {}).get('klines') or []
        if not klines:
            return code, 0
        rows = []
        for line in klines:
            parts = line.split(',')
            if len(parts) >= 7:
                rows.append({
                    'stockCode': code,
                    'tradeDate': parts[0],
                    'mainIn': float(parts[1]),
                    'littleNetIn': float(parts[2]),
                    'mediumNetIn': float(parts[3]),
                    'largeNetIn': float(parts[4]),
                    'superNetIn': float(parts[5]),
                })
        if rows:
            rd.setex(f'market:fund_flow_{code}', TTL, json.dumps(rows, ensure_ascii=False))
        return code, len(rows)
    except Exception as e:
        return code, 0

t0 = time.time()
total_ok = 0
total_rows = 0

print(f'[{datetime.now():%H:%M:%S}] 开始采集 {len(codes)} 只股票资金流向...')
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futs = {ex.submit(fetch_one, c): c for c in codes}
    done = 0
    for fut in as_completed(futs):
        code, n = fut.result()
        done += 1
        if n > 0:
            total_ok += 1
            total_rows += n
        if done % 500 == 0:
            el = time.time() - t0
            print(f'  [{datetime.now():%H:%M:%S}] {done}/{len(codes)}, ok={total_ok}, rows={total_rows}, {el:.0f}s')

el = time.time() - t0
print(f'\n=== 完成 ===')
print(f'成功: {total_ok}/{len(codes)}, 总行数: {total_rows}')
print(f'耗时: {el:.0f}s')
print(f'Redis DBSIZE: {rd.dbsize()}')
