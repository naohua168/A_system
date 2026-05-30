"""验证所有后端 API"""
import urllib.request, json

token = 'eyJhbGciOiJIUzM4NCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJTVVBFUl9BRE1JTiIsInJvbGVMZXZlbCI6NCwiaWF0IjoxNzgwMTA5ODUxLCJleHAiOjE3ODAxOTYyNTF9.Vi4Vuux3LBpfv71I9cuV5hFdz9-wBAZ7tEDZiry3P_l43VYXd2B2HHklsoNI1bZs'
h = {'Authorization': f'Bearer {token}'}

apis = [
    ('大盘指数', '/api/index/list'),
    ('股票列表', '/api/market/list?page=1&size=5'),
    ('行业列表', '/api/market/industries'),
    ('行业排行', '/api/market/sector-ranking'),
    ('最近日期', '/api/market/max-date'),
    ('北向资金', '/api/signal/northbound/latest?days=5'),
    ('题材热点', '/api/signal/hot-reason'),
    ('行业对比', '/api/signal/industry-compare'),
    ('龙虎榜', '/api/signal/dragon-tiger/daily'),
    ('基金列表', '/api/fund/list?page=1&size=5'),
    ('财联社快讯', '/api/info/cls-news?limit=3'),
    ('全球资讯', '/api/info/global-news?limit=3'),
    ('基金净值', '/api/fund/000001.OF/nav?days=5'),
    ('股票详情', '/api/market/600519'),
]

print('=== API 端点验证 ===')
all_ok = True
for name, path in apis:
    try:
        req = urllib.request.Request(f'http://localhost:8082{path}', headers=h)
        resp = urllib.request.urlopen(req, timeout=5)
        body = json.loads(resp.read())
        if isinstance(body, list):
            print(f'  [{name:12s}] ✓ {len(body)} items (list)')
        elif isinstance(body, dict):
            code = body.get('code')
            if code == 200:
                data = body.get('data')
                if isinstance(data, dict):
                    records = data.get('records', data.get('total', '?'))
                    print(f'  [{name:12s}] ✓ code=200 records={records}')
                elif isinstance(data, list):
                    print(f'  [{name:12s}] ✓ code=200 items={len(data)}')
                else:
                    print(f'  [{name:12s}] ✓ code=200 data={data}')
            else:
                all_ok = False
                print(f'  [{name:12s}] ✗ code={code} msg={body.get("message","")}')
        else:
            print(f'  [{name:12s}] ✓ {body}')
    except Exception as e:
        all_ok = False
        print(f'  [{name:12s}] ✗ ERROR: {e}')

print(f'\n整体状态: {"全部通过 ✅" if all_ok else "部分失败 ❌"}')
