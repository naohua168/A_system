"""验证正确的资讯API路径"""
import requests, json

BASE = "http://localhost:8082/api"
r = requests.post(f"{BASE}/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
TOKEN = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {TOKEN}"}

tests = [
    ("GET", "/info/research/000001", "个股研报(正确路径)"),
    ("GET", "/info/news/000001?limit=5", "个股新闻(正确路径)"),
    ("GET", "/info/consensus-eps/000001", "一致预期(正确路径)"),
    ("GET", "/info/cls-news?limit=5", "财联社快讯"),
    ("GET", "/info/global-news?limit=5", "全球资讯"),
]

for method, path, desc in tests:
    r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
    try:
        j = r.json()
        if isinstance(j, dict) and j.get("code") == 200:
            data = j.get("data")
            detail = ""
            if isinstance(data, list):
                detail = f" ({len(data)}条记录)"
            print(f"  ✅ {path} — {desc}{detail}")
        elif isinstance(j, list):
            print(f"  ✅ {path} — {desc} ({len(j)}条)")
        elif isinstance(j, dict) and j.get("code") != 200:
            print(f"  ❌ {path} — {desc}: {j.get('message','')}")
        else:
            print(f"  ⚠️ {path} — {desc}: 返回格式异常: {str(j)[:100]}")
    except:
        print(f"  ❌ {path} — {desc}: HTTP {r.status_code}")
