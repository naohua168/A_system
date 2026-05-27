import requests
BASE = "http://localhost:8082/api"
r = requests.post(BASE+"/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
t = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {t}"}

for d in ["2026-05-27","2026-05-26","2026-05-25"]:
    r = requests.get(f"{BASE}/signal/hot-reason?date={d}", headers=H, timeout=10)
    j = r.json() if r.status_code == 200 else r.text
    if isinstance(j, dict):
        print(f"  {d}: total={j.get('total','?')}, records={len(j.get('records',[]))}")
    elif isinstance(j, list):
        print(f"  {d}: {len(j)} records (list)")
    else:
        print(f"  {d}: {r.text[:100]}")
