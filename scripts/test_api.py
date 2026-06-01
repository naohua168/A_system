"""测试所有后端关键 API"""
import urllib.request, json

tests = {
    'stock_list': '/api/v2/market/list?page=1&size=3',
    'sector_ranking': '/api/v2/market/sector-ranking',
    'industry_treemap': '/api/v2/market/industry-treemap',
    'sector_kline': '/api/v2/market/sector-kline?industry=%E5%9F%BA%E7%A1%80%E5%8C%96%E5%B7%A5',
    'northbound': '/api/v2/signal/northbound/latest?days=1',
    'index_list': '/api/v2/index/list',
    'kline_000001': '/api/v2/market/kline/000001?days=5',
}
for name, path in tests.items():
    try:
        resp = urllib.request.urlopen(f'http://127.0.0.1:8082{path}', timeout=10)
        data = json.loads(resp.read().decode())
        if data.get('code') == 200:
            body = data.get('data', data)
            if isinstance(body, dict):
                records = body.get('records', [body])
            else:
                records = body if isinstance(body, list) else []
            # 检查 changePct 是否已合并
            has_change = any(r.get('changePct') for r in (records[:5] if isinstance(records, list) else [records]))
            print(f'[OK] {name}: {len(records)} records, has_changePct={has_change}')
        else:
            print(f'[ERR] {name}: code={data.get("code")}')
    except Exception as e:
        print(f'[ERR] {name}: {e}')
