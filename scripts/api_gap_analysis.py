#!/usr/bin/env python3
"""分析后端API返回 vs 前端期望的字段差异"""
import requests, json, pymysql, re

BASE = "http://localhost:8082/api"
r = requests.post(f"{BASE}/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
TOKEN = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {TOKEN}"}

def api(method, path, **kw):
    r = requests.request(method, f"{BASE}{path}", headers=H, timeout=10, **kw)
    if r.status_code == 200:
        try: return r.json()
        except: return r.text
    return f"HTTP {r.status_code}"

# ====== 1. 行情列表 /market/list ======
print("="*60)
print("1. /market/list (StockListItem)")
print("="*60)
r = api("GET", "/market/list?page=1&size=1")
rec = (r.get("data",{}).get("records",[]) or [None])[0]
if rec:
    print(f"后端返回字段: {list(rec.keys())}")
    # 前端StockListItem期望: stockCode, stockName, market, industry, price, changePct, change, volume, highPrice, lowPrice, pe, turnoverRate
    expected = {"stockCode","stockName","market","industry","price","changePct","change","volume","highPrice","lowPrice","pe","turnoverRate"}
    missing = expected - set(rec.keys())
    extra = set(rec.keys()) - expected
    if missing: print(f"  前端需要但后端缺少: {missing}")
    if extra: print(f"  后端返回但前端未定义: {extra}")
    if not missing and not extra: print(f"  ✅ 字段完全匹配")
else:
    print(f"  ❌ 无数据")

# ====== 2. 股票详情 /market/{code} ======
print("\n2. /market/000001 (StockDetail)")
r = api("GET", "/market/000001")
rec = r.get("data", {})
print(f"后端返回字段: {list(rec.keys())}")

# ====== 3. 基金列表 /fund/list ======
print("\n3. /fund/list (FundListItem)")
r = api("GET", "/fund/list?page=1&size=1")
rec = (r.get("data",{}).get("records",[]) or [None])[0]
if rec:
    print(f"后端返回字段: {list(rec.keys())}")
    # FundList前端期望: fundCode, fundName, fundType, nav, accumulatedNav, company, manager, establishDate, scale, navDate, yearReturn
    expected = {"fundCode","fundName","fundType","nav","accumulatedNav","company","manager","establishDate","scale","navDate","yearReturn"}
    missing = expected - set(rec.keys())
    extra = set(rec.keys()) - expected
    if missing: print(f"  前端需要但后端缺少: {missing}")
    if extra: print(f"  后端返回但前端未定义: {extra}")
else:
    print(f"  ❌ 无数据")

# ====== 4. 热点 /signal/hot-reason ======
print("\n4. /signal/hot-reason?date=2026-05-25 (HotReason)")
r = api("GET", "/signal/hot-reason?date=2026-05-25")
recs = r.get("date") and r.get("records")
if recs and isinstance(recs, list) and recs:
    rec = recs[0]
    print(f"后端返回字段: {list(rec.keys())}")
else:
    print(f"  返回格式: {json.dumps({k:v for k,v in r.items() if k!='records'}, default=str)}")
    if r.get("records"): print(f"  records数量: {len(r['records'])}")

# ====== 5. 研报 /info/research/000001 ======
print("\n5. /info/research/000001 (ResearchReport)")
r = api("GET", "/info/research/000001")
if isinstance(r, dict) and r.get("records"):
    rec = r["records"][0]
    print(f"后端返回字段: {list(rec.keys())}")
else:
    print(f"  返回: {json.dumps(r, default=str)[:200]}")

# ====== 6. 龙虎榜 /signal/dragon-tiger/daily ======
print("\n6. /signal/dragon-tiger/daily?date=2026-05-25 (DragonTiger)")
r = api("GET", "/signal/dragon-tiger/daily?date=2026-05-25")
if isinstance(r, dict) and r.get("records"):
    rec = r["records"][0]
    print(f"后端返回字段: {list(rec.keys())}")
else:
    print(f"  返回: {json.dumps(r, default=str)[:200]}")

# ====== 7. 公告 /info/filing/000001 ======
print("\n7. /info/filing/000001?limit=1 (Filing)")
r = api("GET", "/info/filing/000001?limit=1")
if isinstance(r, dict) and r.get("records"):
    rec = r["records"][0]
    print(f"后端返回字段: {list(rec.keys())}")
else:
    print(f"  返回: {json.dumps(r, default=str)[:200]}")

# ====== 8. 一致预期 /info/consensus-eps/000001 ======
print("\n8. /info/consensus-eps/000001 (ConsensusEps)")
r = api("GET", "/info/consensus-eps/000001")
if isinstance(r, dict) and r.get("records"):
    rec = r["records"][0]
    print(f"后端返回字段: {list(rec.keys())}")
else:
    print(f"  返回: {json.dumps(r, default=str)[:200]}")

# ====== 9. 概念板块 /signal/concept-blocks/000001 ======
print("\n9. /signal/concept-blocks/000001 (ConceptBlock)")
r = api("GET", "/signal/concept-blocks/000001")
if isinstance(r, list):
    print(f"返回list, {len(r)}条")
    if r: print(f"字段: {list(r[0].keys())}")
else:
    print(f"  返回: {json.dumps(r, default=str)[:200]}")

# ====== 10. 新闻 /info/news/000001 ======
print("\n10. /info/news/000001?limit=1 (News)")
r = api("GET", "/info/news/000001?limit=1")
if isinstance(r, dict) and r.get("records"):
    rec = r["records"][0]
    print(f"后端返回字段: {list(rec.keys())}")
else:
    print(f"  返回: {json.dumps(r, default=str)[:200]}")

# ====== 11. 检查前端types定义 ======
print("\n" + "="*60)
print("前端TypeScript类型定义 vs 后端返回 (关键字段)")
print("="*60)

checks = [
    ("StockListItem", "stock_daily", ["stockCode","stockName","market","industry","price","changePct","change","volume","highPrice","lowPrice","pe","turnoverRate"]),
    ("DragonTiger", "signal_dragon_tiger_detail", ["tradeDate","stockCode","stockName","reason","netBuyWan","buyWan","sellWan","changePct","turnoverPct"]),
    ("HotReason", "signal_hot_reason", ["tradeDate","stockCode","stockName","reason","changePct","turnoverPct"]),
    ("ConsensusEps", "info_consensus_eps", ["stockCode","year","forecastCount","avgEps","minEps","maxEps"]),
    ("Filing", "info_filing", ["stockCode","stockName","title","filingDate","category","url"]),
    ("News", "info_stock_news", ["title","publishTime","contentSummary","source","url"]),
]
for name, table, expected_fields in checks:
    conn2 = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                           database='stock_analysis',charset='utf8mb4')
    cur2 = conn2.cursor()
    cur2.execute(f"DESCRIBE {table}")
    db_cols = {r[0] for r in cur2.fetchall()}
    conn2.close()
    
    missing = set(expected_fields) - db_cols
    if missing:
        print(f"  ❌ {name} ({table}): 前端需要但DB缺少列 {missing}")
    else:
        print(f"  ✅ {name}: 字段匹配")

print("\n分析完成!")
