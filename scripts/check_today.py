"""检查今天的数据可用性"""
import requests, json

BASE = "http://localhost:8082/api"
r = requests.post(BASE+"/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
t = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {t}"}

for path, label in [
    ("/signal/hot-reason?date=2026-05-27", "热点(今天)"),
    ("/signal/hot-reason?date=2026-05-26", "热点(昨天)"),
    ("/signal/hot-reason", "热点(无date)"),
]:
    r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
    d = r.json()
    if isinstance(d, dict):
        print(f"{label}: total={d.get('total','?')}, records={len(d.get('records',[]))}")
    elif isinstance(d, list):
        print(f"{label}: {len(d)}条 (list)")
    else:
        print(f"{label}: {str(d)[:80]}")

# 检查DB数据
import pymysql
conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4')
cur = conn.cursor()
for tbl in ["signal_hot_reason", "signal_dragon_tiger_detail", "signal_daily_industry"]:
    cur.execute(f"SELECT trade_date, COUNT(*) FROM {tbl} WHERE trade_date='2026-05-27' GROUP BY trade_date")
    r = cur.fetchone()
    print(f"DB [{tbl}]: {'无数据' if not r else str(r)}")
conn.close()
