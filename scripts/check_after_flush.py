import subprocess, requests, time

# 清空Redis
r = subprocess.run("docker exec redis redis-cli FLUSHALL", shell=True, capture_output=True, text=True, timeout=5)
print(f"Redis: {r.stdout.strip()}")

time.sleep(1)

BASE = "http://localhost:8082/api"
r = requests.post(BASE+"/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
t = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {t}"}

tests = [
    ("/signal/hot-reason?date=2026-05-27", "热点 今天"),
    ("/signal/industry-compare?date=2026-05-25", "行业对比 05-25"),
    ("/signal/dragon-tiger-detail?date=2026-05-25", "龙虎榜detail"),
    ("/signal/dragon-tiger/daily?date=2026-05-25", "龙虎榜daily"),
]

for path, label in tests:
    r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
    d = r.json()
    if isinstance(d, dict):
        n = d.get("total") or len(d.get("records", []))
        print(f"{label}: {n}条")
    elif isinstance(d, list):
        print(f"{label}: {len(d)}条")
    else:
        print(f"{label}: {r.text[:80]}")
