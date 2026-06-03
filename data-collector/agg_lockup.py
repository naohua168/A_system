"""
聚合个股锁解数据到 lockup_upcoming
"""
import json, subprocess, datetime

TTL = 86400  # 24h

def redis_get(key):
    r = subprocess.run(['redis-cli', '-h', 'redis', 'GET', key],
        capture_output=True, timeout=10, text=True)
    out = r.stdout.strip()
    if not out or out == 'nil':
        return None
    try: return json.loads(out)
    except: return None

def redis_setex(key, ttl, val):
    dump = json.dumps(val, ensure_ascii=False)
    r = subprocess.run(['redis-cli', '-h', 'redis', '-x', 'SETEX', key, str(ttl)],
        input=dump.encode(), capture_output=True, timeout=10)
    return r.returncode == 0

# 获取所有 lockup_* key
r = subprocess.run(['redis-cli', '-h', 'redis', 'KEYS', 'market:lockup_*'],
    capture_output=True, timeout=30, text=True)
keys = [k for k in r.stdout.strip().split('\n') if k and k != 'market:lockup_upcoming']
print(f'lockup keys: {len(keys)}')

# 聚合锁解数据
today = datetime.date.today().isoformat()
result = []
seen = set()

for key in keys:
    data = redis_get(key)
    if not data:
        continue
    if isinstance(data, dict):
        data = [data]
    for item in data:
        ld = str(item.get('lockupDate', '') or item.get('tradeDate', '') or '')
        code = str(item.get('stockCode', '') or '')
        if not code or not ld:
            continue
        if ld < today:
            continue
        if code in seen:
            continue
        seen.add(code)
        result.append({
            'stockCode': code,
            'stockName': str(item.get('stockName', '') or ''),
            'lockupDate': ld[:10],
            'lockupType': str(item.get('lockupType', '') or item.get('FREE_SHARES_TYPE', '') or '限售股'),
            'shares': float(item.get('shares', 0) or item.get('CURRENT_FREE_SHARES', 0) or 0),
            'floatRatio': float(item.get('floatRatio', 0) or item.get('float_ratio', 0) or 0),
        })

# 按解禁日期排序
result.sort(key=lambda x: x['lockupDate'])

# 从 stock_basic 补全股票名
sb = redis_get('market:stock_basic')
if sb:
    name_map = {s.get('stockCode',''): s.get('stockName','') for s in sb}
    for r2 in result:
        if not r2['stockName'] and r2['stockCode'] in name_map:
            r2['stockName'] = name_map[r2['stockCode']]

print(f'聚合结果: {len(result)} 条')
if result:
    print(f'  最早: {result[0]["lockupDate"]} {result[0]["stockName"]}')
    print(f'  最晚: {result[-1]["lockupDate"]} {result[-1]["stockName"]}')
    written = redis_setex('market:lockup_upcoming', TTL, result)
    print(f'写入Redis: {"成功" if written else "失败"}, TTL={TTL}s ({TTL//3600}h)')
else:
    print('无有效数据')
