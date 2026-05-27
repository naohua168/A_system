"""验证关键端点的实际响应"""
import requests, json

BASE = "http://localhost:8082/api"
r = requests.post(f"{BASE}/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
T = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {T}"}

tests = [
    "/signal/hot-reason?date=2026-05-25",
    "/signal/dragon-tiger/daily?date=2026-05-25",
    "/signal/northbound/date?date=2026-05-25",
    "/signal/lockup-detail/000001",
    "/signal/fund-flow/000001?limit=1",
    "/signal/concept-blocks/000001",
    "/info/filing/000001?limit=1",
    "/info/consensus-eps/000001",
    "/info/news/000001?limit=1",
]

for path in tests:
    r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
    d = r.json()
    desc = ""
    if isinstance(d, list):
        desc = f"{len(d)}条记录"
        if d: desc += f", 字段={list(d[0].keys())[:6]}"
    elif isinstance(d, dict):
        if "records" in d: desc = f"records={len(d['records'])}, total={d.get('total','?')}, 字段={list(d['records'][0].keys())[:6] if d['records'] else '[]'}"
        elif "code" in d: desc = f"code={d.get('code')}, msg={d.get('message','')}"
        elif "data" in d: desc = f"data={d.get('data')}"
        else: desc = str(list(d.keys())[:5])
    else: desc = str(d)[:100]
    print(f"  {'✅' if '500' not in desc and 'records=0' not in desc else '❌'} {path}: {desc}")
