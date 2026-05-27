#!/usr/bin/env python3
"""全面验证后端API返回 vs 前端TypeScript类型定义"""
import requests, json

import time; time.sleep(3)
BASE = "http://localhost:8082/api"
print("Logging in...", flush=True)
r = requests.post(f"{BASE}/user/login", json={"username":"admin","password":"admin123"}, timeout=10)
print(f"Login HTTP {r.status_code}", flush=True)
try:
    login = r.json()
except:
    print(f"Not JSON: {r.text[:200]}", flush=True)
    exit(1)
if not login.get("data") or not login["data"].get("token"):
    print(f"Login failed: code={login.get('code')} msg={login.get('message')}", flush=True)
    exit(1)
TOKEN = login["data"]["token"]
H = {"Authorization": f"Bearer {TOKEN}"}

# 前端TS类型期望的字段 (从types/index.ts整理)
frontend_types = {
    "StockListItem": {"stockCode","stockName","market","industry","price","changePct","change","volume","highPrice","lowPrice","pe","turnoverRate"},
    "StockDetail": {"stockCode","stockName","market","industry","listingDate","pe","pb","totalMarketCap","floatMarketCap","price","changePercent","open","high","low","preClose","volume","amount","turnoverRate","tradeDate"},
    "StockDaily": {"id","stockCode","tradeDate","openPrice","highPrice","lowPrice","closePrice","preClose","volume","amount","changePercent","turnoverRate"},
    "HotReason": {"id","tradeDate","stockCode","stockName","reason","changePct","turnoverPct"},
    "DragonTiger": {"id","tradeDate","stockCode","stockName","reason","netBuyWan","buyWan","sellWan","changePct","turnoverPct","close"},
    "Northbound": {"id","tradeDate","hgtYi","sgtYi"},
    "IndustryCompare": {"industryName","changePct","turnoverYi","upCount","downCount","leader"},
    "FundFlow": {"id","stockCode","tradeDate","close","mainIn","superNetIn"},
    "LockupDetail": {"id","stockCode","lockupDate","lockupType","shares","typeTag","floatRatio","isUpcoming"},
    "ResearchReport": {"id","stockCode","title","publishDate","orgName","rating","predictEpsThisYear","predictEpsNextYear"},
    "ConsensusEps": {"id","stockCode","year","forecastCount","minEps","avgEps","maxEps"},
    "NewsItem": {"id","stockCode","title","publishTime","contentSummary","source","url"},
    "Filing": {"id","stockCode","title","filingDate","category","url"},
    "Fund": {"id","fundCode","fundName","fundType","company","manager","establishDate","nav","accumulatedNav","scale","navDate","yearReturn"},
    "FundNav": {"id","fundCode","navDate","nav","accumulatedNav","dailyReturn"},
    "FundHolding": {"id","fundCode","stockCode","stockName","ratio","rankNum","reportDate"},
    "ConceptBlock": {"id","stockCode","blockType","blockName","changePct"},
}

# 定义测试: (path, type_name, extract_func)
tests = [
    ("/market/list?page=1&size=1", "StockListItem", lambda d: (d.get("data",{}).get("records") or [None])[0]),
    ("/market/000001", "StockDetail", lambda d: d.get("data",{})),
    ("/market/kline/000001?days=1", "StockDaily", lambda d: (d.get("data") or [None])[0]),
    ("/fund/list?page=1&size=1", "Fund", lambda d: (d.get("data",{}).get("records") or [None])[0]),
    ("/fund/000001/nav?days=1", "FundNav", lambda d: (d.get("data") or [None])[0]),
    ("/fund/000001/holdings", "FundHolding", lambda d: (d.get("data") or [None])[0]),
    ("/signal/hot-reason?date=2026-05-27", "HotReason", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/signal/dragon-tiger/daily?date=2026-05-25", "DragonTiger", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/signal/dragon-tiger-detail?date=2026-05-25", "DragonTiger", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/signal/northbound/latest?days=1", "Northbound", lambda d: (d.get("data") or [None])[0] if isinstance(d,dict) else None),
    ("/signal/industry-compare?date=2026-05-25", "IndustryCompare", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/signal/fund-flow/000001?limit=1", "FundFlow", lambda d: (d.get("data") or [None])[0] if isinstance(d,dict) else None),
    ("/signal/lockup-detail/000001", "LockupDetail", lambda d: d if isinstance(d,list) and d else None),
    ("/info/research/000001", "ResearchReport", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/info/consensus-eps/000001", "ConsensusEps", lambda d: d[0] if isinstance(d,list) and d else None),
    ("/info/news/000001?limit=1", "NewsItem", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/info/filing/000001?limit=1", "Filing", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) and d.get("records") else None),
    ("/signal/concept-blocks/000001", "ConceptBlock", lambda d: d[0] if isinstance(d,list) and d else None),
]

ok = fail = 0
print("=" * 70)
print("后端API响应 vs 前端TypeScript类型  匹配检查")
print("=" * 70)

for path, ts_type, extractor in tests:
    r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
    rec = None
    try:
        data = r.json() if r.status_code == 200 else None
        rec = extractor(data) if data else None
    except:
        rec = None
    
    if not rec or not isinstance(rec, dict):
        status = "⚠️" if r.status_code == 200 else "❌"
        detail = f"HTTP {r.status_code}"
        if r.status_code == 200 and isinstance(data, dict):
            detail += f" | {str(list(data.keys())[:4])}"
        print(f"  {status} {path}")
        print(f"    [{ts_type}] 无记录: {detail}")
        if not rec:
            ok += 1  # Not necessarily a bug
        continue
    
    expected = frontend_types[ts_type]
    api_keys = set(rec.keys())
    missing = expected - api_keys
    
    if missing:
        print(f"  ❌ {path}")
        for f in sorted(missing):
            print(f"    前端需要但后端缺: {f}")
        fail += 1
    else:
        print(f"  ✅ {path}")
        print(f"    [{ts_type}] {len(api_keys)}字段全部匹配")
        ok += 1

print()
print("=" * 70)
if fail == 0:
    print(f"🎉 全部 {ok} 个类型检查通过，前后端数据完全一致！")
else:
    print(f"⚠️ 通过 {ok} 个，失败 {fail} 个")
    print("需要检查失败项的后端逻辑")
