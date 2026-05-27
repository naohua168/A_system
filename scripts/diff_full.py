#!/usr/bin/env python3
"""全面分析前后端数据差异 - 对比API响应 vs 前端TS类型"""
import requests, json

BASE = "http://localhost:8082/api"
r = requests.post(f"{BASE}/user/login", json={"username":"admin","password":"admin123"}, timeout=5)
TOKEN = r.json()["data"]["token"]
H = {"Authorization": f"Bearer {TOKEN}"}

def get(path):
    r = requests.get(f"{BASE}{path}", headers=H, timeout=10)
    if r.status_code == 200:
        try: return r.json()
        except: return None
    return None

# ====== 前端期望的类型字段定义 (从TS整理) ======
types = {
    "StockListItem": {"stockCode","stockName","market","industry","price","changePct","change","volume","highPrice","lowPrice","pe","turnoverRate"},
    "StockDetail": {"stockCode","stockName","market","industry","listingDate","pe","pb","totalMarketCap","floatMarketCap","price","changePercent","open","high","low","preClose","volume","amount","turnoverRate","tradeDate"},
    "StockDaily": {"id","stockCode","tradeDate","openPrice","highPrice","lowPrice","closePrice","preClose","volume","amount","changePercent","turnoverRate"},
    "Fund": {"id","fundCode","fundName","fundType","company","manager","establishDate","nav","accumulatedNav","scale","navDate","yearReturn"},
    "FundNav": {"id","fundCode","navDate","nav","accumulatedNav","dailyReturn"},
    "FundHolding": {"id","fundCode","stockCode","stockName","ratio","rankNum","reportDate"},
    "HotReason": {"id","tradeDate","stockCode","stockName","reason","changePct","turnoverPct"},
    "DragonTiger": {"id","tradeDate","stockCode","stockName","reason","netBuyWan","changePct","turnoverPct"},
    "DragonTigerDetail": {"id","tradeDate","stockCode","stockName","reason","netBuyWan","buyWan","sellWan","changePct","turnoverPct","close"},
    "Northbound": {"id","tradeDate","hgtYi","sgtYi"},
    "LockupDetail": {"id","stockCode","lockupDate","lockupType","shares","typeTag","floatRatio","isUpcoming"},
    "IndustryCompare": {"industryName","changePct","turnoverYi","upCount","downCount","leader"},
    "ResearchReport": {"id","stockCode","title","publishDate","orgName","rating","predictEpsThisYear","predictEpsNextYear"},
    "ConsensusEps": {"id","stockCode","year","forecastCount","minEps","avgEps","maxEps"},
    "NewsItem": {"id","stockCode","title","publishTime","contentSummary","source","url"},
    "Filing": {"id","stockCode","title","filingDate","category","url"},
    "ConceptBlock": {"id","stockCode","blockType","blockName","changePct"},
    "FundFlow": {"id","stockCode","tradeDate","close","mainIn","superNetIn"},
}

# ====== 测试API端点 ======
tests = [
    ("/market/list?page=1&size=1", "StockListItem", lambda d: d.get("data",{}).get("records",[None])[0]),
    ("/market/000001", "StockDetail", lambda d: d.get("data",{})),
    ("/market/kline/000001?days=1", "StockDaily", lambda d: (d.get("data") or [None])[0]),
    ("/fund/list?page=1&size=1", "Fund", lambda d: (d.get("data",{}).get("records",[]) or [None])[0]),
    ("/fund/000001/nav?days=1", "FundNav", lambda d: (d.get("data") or [None])[0]),
    ("/fund/000001/holdings", "FundHolding", lambda d: (d.get("data") or [None])[0]),
    ("/signal/hot-reason?date=2026-05-25", "HotReason", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else (d[0] if isinstance(d,list) and d else None)),
    ("/signal/dragon-tiger/daily?date=2026-05-25", "DragonTiger", lambda d: (d.get("records") or [None])[0]),
    ("/signal/dragon-tiger-detail?date=2026-05-25", "DragonTigerDetail", lambda d: (d.get("records") or [None])[0]),
    ("/signal/northbound/latest?days=1", "Northbound", lambda d: (d.get("data") or [None])[0]),
    ("/signal/lockup/stock/000001", "LockupDetail", lambda d: (d.get("data") or [None])[0]),
    ("/signal/industry-compare?date=2026-05-25", "IndustryCompare", lambda d: (d.get("records") or [None])[0]),
    ("/info/research/000001", "ResearchReport", lambda d: (d.get("records") or [None])[0]),
    ("/info/consensus-eps/000001", "ConsensusEps", lambda d: d[0] if isinstance(d,list) and d else None),
    ("/info/news/000001?limit=1", "NewsItem", lambda d: (d.get("records") or [None])[0] if isinstance(d,dict) else None),
    ("/info/filing/000001?limit=1", "Filing", lambda d: None),
    ("/signal/concept-blocks/000001", "ConceptBlock", lambda d: d[0] if isinstance(d,list) and d else None),
    ("/signal/fund-flow/000001?limit=1", "FundFlow", lambda d: (d.get("data") or [None])[0]),
]

print("="*70)
print("前后端数据差异分析")
print("="*70)

issues = []
for path, ts_type, extractor in tests:
    data = get(path)
    if data is None:
        print(f"  ❌ {path} → HTTP失败")
        continue
    
    try:
        rec = extractor(data)
    except:
        rec = None
    if rec is None or rec == {}:
        print(f"  ⚠️ {path} → 无记录 (type={ts_type})")
        if isinstance(data, dict) and "message" in data:
            print(f"     错误: {data.get('message')}")
        continue
    
    api_fields = set(rec.keys()) if isinstance(rec, dict) else set()
    expected = types[ts_type]
    
    # Missing: frontend needs but API doesn't return
    missing = expected - api_fields
    # Extra: API returns but frontend doesn't expect
    extra = api_fields - expected
    
    status = "✅"
    if missing: status = "⚠️"
    if not api_fields: status = "❌"
    
    print(f"  {status} {path}")
    for f in sorted(missing): 
        print(f"    前端需要但后端缺: {f}")
        issues.append((path, ts_type, f, "MISSING"))
    for f in sorted(extra - {"createdAt","updatedAt","id"}): 
        print(f"    后端返回但前端未装: {f}")
        issues.append((path, ts_type, f, "EXTRA"))

print()
print("="*70)
if not issues:
    print("🎉 所有类型完全匹配！")
else:
    print(f"📋 共 {len(issues)} 个差异:")
    for path, ts, field, typ in issues:
        print(f"  [{typ}] {path} ({ts}): {field}")
