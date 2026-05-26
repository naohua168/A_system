"""调试失败的API端点"""
import requests

BASE = "http://localhost:8082/api"
r = requests.post(f"{BASE}/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
TOKEN = r.json()["data"]["token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# 1. 龙虎榜daily - 检查为什么是0条
print("=== 1. 龙虎榜daily 2026-05-25 ===")
r = requests.get(f"{BASE}/signal/dragon-tiger/daily?date=2026-05-25", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 2. 题材热点
print("=== 2. 题材热点 ===")
r = requests.get(f"{BASE}/signal/hot-reason?date=2026-05-25", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 3. 板块K线 (银行)
print("=== 3. 板块K线 银行 ===")
r = requests.get(f"{BASE}/market/sector-kline?industry=%E9%93%B6%E8%A1%8C&days=5", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 4. 个股研报
print("=== 4. 个股研报 000001 ===")
r = requests.get(f"{BASE}/info/research/000001", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 5. 个股新闻
print("=== 5. 个股新闻 000001 ===")
r = requests.get(f"{BASE}/info/news/000001", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 6. 一致预期
print("=== 6. 一致预期 000001 ===")
r = requests.get(f"{BASE}/info/consensus-eps/000001", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 7. 行业对比
print("=== 7. 行业对比 ===")
r = requests.get(f"{BASE}/signal/industry-compare?date=2026-05-25", headers=HEADERS, timeout=10)
print(f"状态码: {r.status_code}")
print(f"响应: {r.text[:500]}")
print()

# 8. DB查询验证
print("=== 8. 数据库查询验证 ===")
import pymysql
conn = pymysql.connect(host="localhost", port=3307, user="root", password="hadoop123",
                       database="stock_analysis", charset="utf8mb4")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM signal_dragon_tiger_detail WHERE trade_date='2026-05-25'")
print(f"龙虎榜 2026-05-25: {cur.fetchone()[0]}条")

cur.execute("SELECT COUNT(*) FROM signal_hot_reason WHERE trade_date='2026-05-25'")
print(f"题材热点 2026-05-25: {cur.fetchone()[0]}条")

cur.execute("SELECT DISTINCT trade_date FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 5")
print(f"题材热点最近日期: {[r[0] for r in cur.fetchall()]}")

cur.execute("SELECT COUNT(*) FROM signal_daily_industry")
print(f"行业对比数据: {cur.fetchone()[0]}条")

cur.execute("SELECT stock_code, COUNT(*) FROM info_research_report GROUP BY stock_code ORDER BY COUNT(*) DESC LIMIT 5")
print(f"研报最多的股票: {cur.fetchall()}")

cur.execute("SELECT stock_code, COUNT(*) FROM info_stock_news GROUP BY stock_code ORDER BY COUNT(*) DESC LIMIT 5")
print(f"新闻最多的股票: {cur.fetchall()}")

cur.execute("SELECT stock_code, COUNT(*) FROM info_consensus_eps GROUP BY stock_code ORDER BY COUNT(*) DESC LIMIT 5")
print(f"一致预期最多的股票: {cur.fetchall()}")

# 查一下000001的数据
cur.execute("SELECT COUNT(*) FROM info_research_report WHERE stock_code='1' OR stock_code='000001'")
print(f"平安银行研报: {cur.fetchone()[0]}条")

cur.execute("SELECT stock_code, title FROM info_research_report WHERE stock_code='000001' LIMIT 3")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
if cur.rowcount == 0:
    cur.execute("SELECT stock_code, title FROM info_research_report LIMIT 3")
    print(f"任意研报示例:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

conn.close()
