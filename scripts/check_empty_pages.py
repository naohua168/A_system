"""检查各页面API数据是否为空"""
import requests, time

BASE = "http://localhost:8082/api"
r = requests.post(BASE+"/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
t = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {t}"}

tests = {
    "首页-热门股票": "/market/list?page=1&size=5",
    "首页-指数": "/index/list",
    "首页-热点题材": "/signal/hot-reason?date=2026-05-27",
    "首页-行业对比": "/signal/industry-compare?date=2026-05-27",
    "首页-基金": "/fund/list?page=1&size=3",
    "首页-龙虎榜": "/signal/dragon-tiger-detail?date=2026-05-25",
    "股票列表": "/market/list?page=1&size=20",
    "基金列表": "/fund/list?page=1&size=20",
    "K线": "/market/kline/000001?days=60",
    "龙虎榜详情": "/signal/dragon-tiger-detail?date=2026-05-25",
    "题材热点": "/signal/hot-reason?date=2026-05-27",
    "北向资金": "/signal/northbound/latest?days=5",
    "资金流向": "/signal/fund-flow/000001?limit=10",
    "限售解禁": "/signal/lockup-detail/000001",
    "一致预期": "/info/consensus-eps/000001",
    "个股新闻": "/info/news/000001?limit=10",
    "行业对比页": "/signal/industry-compare?date=2026-05-25",
    "财联社快讯": "/info/cls-news?limit=10",
}

print("=" * 60)
print("页面数据渲染检查")
print("=" * 60)

empty_pages = []
for label, path in tests.items():
    try:
        r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
        d = r.json() if r.status_code == 200 else None
        
        is_empty = False
        detail = ""
        
        if d is None:
            is_empty = True
            detail = f"HTTP {r.status_code}"
        elif isinstance(d, list):
            is_empty = len(d) == 0
            detail = f"{len(d)}条"
        elif isinstance(d, dict):
            if "records" in d:
                recs = d.get("records", [])
                is_empty = len(recs) == 0
                detail = f"{len(recs)}条"
            elif "data" in d and isinstance(d["data"], dict):
                recs = d["data"].get("records", [])
                is_empty = len(recs) == 0
                detail = f"{len(recs)}条 (分页)"
            elif "data" in d and isinstance(d["data"], list):
                is_empty = len(d["data"]) == 0
                detail = f"{len(d['data'])}条 (data)"
            elif "code" in d:
                is_empty = d.get("code") != 200
                detail = f"code={d.get('code')}, msg={d.get('message','')}"
            else:
                if "total" in d:
                    detail = f"total={d['total']}"
                else:
                    detail = f"keys={list(d.keys())[:3]}"
        
        status = "❌ 空" if is_empty else "✅"
        print(f"  {status} {label}: {detail}")
        if is_empty:
            empty_pages.append(label)
    except Exception as e:
        print(f"  ❌ {label}: ERROR - {e}")
        empty_pages.append(label)

print()
if empty_pages:
    print(f"发现 {len(empty_pages)} 个无数据页面:")
    for p in empty_pages:
        print(f"  ❌ {p}")
else:
    print("🎉 所有页面数据正常!")
