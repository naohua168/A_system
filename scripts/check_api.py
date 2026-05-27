import requests
BASE = "http://localhost:8082/api"
r = requests.post(BASE + "/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
t = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {t}"}

# 1. Filing
r = requests.get(f"{BASE}/info/filing/000001?limit=1", headers=H, timeout=10)
print(f"Filing: HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json()
    if d.get("code") == 200:
        print(f"  OK! total={d.get('data',{}).get('total','?')}")
    else:
        print(f"  Error: {d.get('message')}")

# 2. Fund list
r = requests.get(f"{BASE}/fund/list?page=1&size=1", headers=H, timeout=10)
d = r.json()
rec = (d.get("data",{}).get("records",[]) or [None])[0]
if rec:
    print(f"Fund keys: {list(rec.keys())}")
    print(f"  navDate={rec.get('navDate')}, yearReturn={rec.get('yearReturn')}")

# 3. Market list
r = requests.get(f"{BASE}/market/list?page=1&size=1", headers=H, timeout=10)
d = r.json()
rec = (d.get("data",{}).get("records",[]) or [None])[0]
if rec:
    print(f"Market keys: {list(rec.keys())}")
    print(f"  has market={rec.get('market','MISSING')}")
