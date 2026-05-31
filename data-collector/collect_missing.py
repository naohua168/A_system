"""快速采集缺失数据：龙虎榜、指数、行业归属"""
import sys, os, json, csv, time, random, re, urllib.request
from pathlib import Path
from datetime import datetime
sys.path.insert(0, '/app/pylib')

CSV_DIR = Path('/data/raw')
UA = "Mozilla/5.0"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EM_MIN_INTERVAL = 0.5
_em_last_call = [0.0]

def em_get(url, params=None, timeout=15):
    import requests
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0: time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        sess = requests.Session()
        sess.headers.update({"User-Agent": UA})
        return sess.get(url, params=params, timeout=timeout)
    finally:
        _em_last_call[0] = time.time()

def save_csv(name, rows):
    if not rows: return print(f'  {name}: 0 条')
    fp = CSV_DIR / f'{name}_{datetime.now():%Y%m%d_%H%M%S}.csv'
    with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f'  {name}: {len(rows)} 条 -> {fp.name}')

# 1. 龙虎榜
def collect_dragon_tiger(trade_date=None):
    if trade_date is None: trade_date = datetime.now().strftime("%Y-%m-%d")
    params = {"reportName":"RPT_DAILYBILLBOARD_DETAILSNEW",
        "filter": f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
        "pageSize": "500","sortColumns":"BILLBOARD_NET_AMT","sortTypes":"-1",
        "columns":"ALL","pageNumber":"1","source":"WEB","client":"WEB"}
    r = em_get(DATACENTER_URL, params=params)
    if not r or not r.text: return []
    d = r.json()
    if not isinstance(d, dict): return []
    items = (d.get("result") or {}).get("data") or []
    rows = []
    for row in items:
        rows.append({"trade_date": str(row.get("TRADE_DATE",""))[:10],
            "stock_code": row.get("SECURITY_CODE",""), "stock_name": row.get("SECURITY_NAME_ABBR",""),
            "reason": row.get("EXPLANATION",""), "net_buy_wan": round((row.get("BILLBOARD_NET_AMT") or 0)/10000, 1),
            "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0)/10000, 1),
            "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0)/10000, 1),
            "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2)})
    return rows

# 2. 指数行情
INDEX_CODES = [('sh000001','上证指数'),('sz399001','深证成指'),('sz399006','创业板指'),('sh000688','科创50'),('sh000300','沪深300')]
def collect_index_quote():
    codes = [c[0] for c in INDEX_CODES]
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("gbk")
    except: return []
    result = []
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line: continue
        vals = line.split('"')[1].split("~")
        if len(vals) < 40: continue
        key = line.split("=")[0].split("_")[-1]
        name = None
        for ic, iname in INDEX_CODES:
            if ic.endswith(key): name = iname; break
        result.append({"index_code": key, "index_name": name or vals[1],
            "price": vals[3] or 0, "change_pct": vals[32] or 0,
            "open": vals[5] or 0, "high": vals[33] or 0, "low": vals[34] or 0,
            "volume": vals[6] or 0, "amount": vals[37] or 0})
    return result

# 3. 指数K线
def collect_index_kline(code):
    import requests
    prefix = "sh" if code.startswith(("0","6","9")) else "sz"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,120,qfq"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        d = r.json()
    except: return []
    if not isinstance(d, dict): return []
    data = d.get("data")
    if not isinstance(data, dict): return []
    klines = (data.get(code) or data.get(prefix+code) or {}).get("day",[])
    if not klines:
        qt = data.get("qt", {})
        if isinstance(qt, dict):
            klines = (qt.get(code) or qt.get(prefix+code) or {}).get("day",[]) or []
    rows = []
    for k in klines:
        if isinstance(k, (list, tuple)) and len(k) >= 6:
            rows.append({"index_code": code, "trade_date": str(k[0]).replace("-",""),
                "open": k[1], "close": k[2], "high": k[3], "low": k[4],
                "volume": k[5] if len(k)>5 else 0, "amount": k[6] if len(k)>6 else 0,
                "change_pct": round((float(k[2])-float(k[1]))/float(k[1])*100,2) if float(k[1])>0 else 0})
    return rows

# 4. 股票行业归属
def collect_stock_industries(codes):
    all_rows = []
    for i in range(0, len(codes), 100):
        batch = codes[i:i+100]
        prefixed = [f"{'sh' if c.startswith(('6','9')) else 'bj' if c.startswith('8') else 'sz'}{c}" for c in batch]
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read().decode("gbk")
        except: time.sleep(0.5); continue
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line: continue
            vals = line.split('"')[1].split("~")
            if len(vals) < 45: continue
            code = vals[2]; industry = vals[43] if len(vals) > 43 else ""
            if industry and industry.strip():
                all_rows.append({"stock_code": code, "industry": industry, "industry_en": ""})
        time.sleep(0.5)
    return all_rows

print('=== 快速采集缺失数据 ===')
# 1. 龙虎榜
print('\n1. 龙虎榜...')
dt = collect_dragon_tiger()
save_csv('dragon_tiger', dt)
time.sleep(1)

# 2. 指数行情 + K线
print('\n2. 指数行情...')
idx = collect_index_quote()
save_csv('tencent_index', idx)
print('\n3. 指数K线...')
all_k = []
for ic, _ in INDEX_CODES:
    kl = collect_index_kline(ic)
    if kl: all_k.extend(kl); print(f'  {ic}: {len(kl)}天')
    time.sleep(0.3)
save_csv('index_daily', all_k)

# 4. 行业归属
print('\n4. 股票行业归属...')
try:
    from pyhive import hive
    c = hive.connect(host='hive-server', port=10000).cursor()
    c.execute("SELECT stock_code, stock_name FROM stock_basic ORDER BY stock_code")
    stocks = [r[0] for r in c.fetchall()]
    print(f'  从 Hive 读取 {len(stocks)} 只股票')
    inds = collect_stock_industries(stocks)
    save_csv('stock_industry', inds)
except Exception as e:
    print(f'  行业归属采集失败: {e}')

print(f'\n=== 采集完成 {datetime.now():%H:%M:%S} ===')
