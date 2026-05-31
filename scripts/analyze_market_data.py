"""分析 Redis 中市场数据的内容和质量"""
import json, redis

r = redis.Redis(host='redis', port=6379, db=0)

def analyze(key, limit=3):
    raw = r.get(key)
    if not raw:
        return '❌ 不存在'
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            sample = data[:limit]
            fields = list(sample[0].keys()) if sample else []
            return f'✅ {len(data)}条, 字段: {fields}, 样例: {sample}'
        elif isinstance(data, dict):
            return f'✅ 字典, 键: {list(data.keys())[:5]}'
        return f'✅ 类型: {type(data).__name__}'
    except json.JSONDecodeError as e:
        return f'❌ JSON解析失败: {e}'

keys = sorted(r.keys('market:*'))
for k in keys:
    if k.startswith(b'market:kline_'):
        continue  # 单独处理
    print(f'  {k.decode()}: {analyze(k)}')

print('\n--- K线数据抽样 ---')
klines = [k for k in keys if k.startswith(b'market:kline_')]
print(f'  共有 {len(klines)} 只股票有K线数据')
if klines:
    sample = r.get(klines[0])
    if sample:
        data = json.loads(sample)
        print(f'  样例 {klines[0].decode()}: {len(data)}个交易日')
        print(f'  日期范围: {data[0].get("trade_date","?")} ~ {data[-1].get("trade_date","?")}')
        print(f'  首条: {data[0]}')

print(f'\n--- 整体概况 ---')
print(f'  Redis DBSIZE: {r.dbsize()}')
print(f'  数据种类: {len([k for k in keys if not k.startswith(b"market:kline_")])} 类')
