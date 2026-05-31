"""
资金流向CSV导入管道（手动导入）
从 /data/raw/fund_flow_*.csv 读取数据 → 写入 Redis market:fund_flow_{code}

CSV 期望列名（支持 snake_case 或 camelCase）：
  stock_code, trade_date, main_net, small_net, mid_net, large_net, super_net
  或: stockCode, tradeDate, mainIn, littleNetIn, mediumNetIn, largeNetIn, superNetIn
"""
import sys, json, glob, csv, os
sys.path.insert(0, '/app/pylib')
import redis

rd = redis.Redis(host='redis', port=6379, db=0)
TTL = 604800

CSV_DIR = '/data/raw'
PATTERN = 'fund_flow_*.csv'

FIELD_MAP = {
    'stock_code': 'stockCode', 'stockcode': 'stockCode',
    'trade_date': 'tradeDate', 'tradedate': 'tradeDate',
    'date': 'tradeDate',
    'main_net': 'mainIn', 'mainnet': 'mainIn',
    'small_net': 'littleNetIn', 'smallnet': 'littleNetIn',
    'mid_net': 'mediumNetIn', 'midnet': 'mediumNetIn',
    'large_net': 'largeNetIn', 'largenet': 'largeNetIn',
    'super_net': 'superNetIn', 'supernet': 'superNetIn',
    'main_in': 'mainIn', 'mainin': 'mainIn',
    'little_net_in': 'littleNetIn',
    'medium_net_in': 'mediumNetIn',
    'large_net_in': 'largeNetIn',
    'super_net_in': 'superNetIn',
}

files = sorted(glob.glob(os.path.join(CSV_DIR, PATTERN)))
if not files:
    print(f'❌ 未找到 fund_flow_*.csv 文件，请放入 {CSV_DIR}/ 目录')
    print('CSV 列名: stock_code, trade_date, main_net, small_net, mid_net, large_net, super_net')
    sys.exit(1)

fp = files[-1]
print(f'读取: {fp}')

with open(fp, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f'总行数: {len(rows)}')

# 按 stock_code 分组
by_code = {}
for row in rows:
    code = row.get('stock_code', '') or row.get('stockCode', '') or row.get('code', '')
    if not code:
        continue
    normalized = {}
    for k, v in row.items():
        target_key = FIELD_MAP.get(k.lower().strip(), k)
        # 自动 camelCase 转换（以防有未列出的 snake_case 列）
        parts = target_key.split('_')
        if len(parts) > 1:
            target_key = parts[0] + ''.join(p.capitalize() for p in parts[1:])
        try:
            v = float(v) if v and v.replace('.', '', 1).replace('-', '', 1).lstrip('-').isdigit() else v
        except (ValueError, AttributeError):
            pass
        normalized[target_key] = v
    by_code.setdefault(code, []).append(normalized)

written = 0
for code, items in by_code.items():
    items.sort(key=lambda x: str(x.get('tradeDate', '')), reverse=True)
    rd.setex(f'market:fund_flow_{code}', TTL, json.dumps(items, ensure_ascii=False))
    written += 1

print(f'✅ 写入 {written} 只股票的资金流向数据')
print(f'原始行数: {len(rows)}, Redis DBSIZE: {rd.dbsize()}')
