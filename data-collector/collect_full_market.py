"""
全市场真实数据采集器
使用 a-stock-data 方法从 13 个数据源采集缺失数据
输出 CSV → HDFS → Hive → Redis 管道
"""
import sys, os, json, csv, time, random, re, uuid, secrets
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import requests
import urllib.request

# ========== 配置 ==========
CSV_DIR = Path('/data/raw')
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EM_MIN_INTERVAL = 0.5
_em_last_call = [0.0]

# ========== 工具函数 ==========
def em_get(url, params=None, headers=None, timeout=15):
    """东财统一防封入口"""
    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        sess = requests.Session()
        sess.headers.update({"User-Agent": UA})
        return sess.get(url, params=params, headers=headers, timeout=timeout)
    finally:
        _em_last_call[0] = time.time()

def em_datacenter(report_name, filter_str="", page_size=50, sort_columns="", sort_types="-1"):
    """东财数据中心查询"""
    params = {
        "reportName": report_name, "columns": "ALL",
        "filter": filter_str, "pageNumber": "1", "pageSize": str(page_size),
        "sortColumns": sort_columns, "sortTypes": sort_types,
        "source": "WEB", "client": "WEB",
    }
    r = em_get(DATACENTER_URL, params=params, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    if isinstance(d.get("result"), dict) and d["result"].get("data"):
        return d["result"]["data"]
    return []

def save_csv(name, rows):
    """保存为 CSV 文件"""
    if not rows:
        print(f'  {name}: 0 条，跳过')
        return
    fp = CSV_DIR / f'{name}_{datetime.now():%Y%m%d_%H%M%S}.csv'
    with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f'  {name}: {len(rows)} 条 → {fp.name}')

def get_prefix(code):
    return "sh" if code.startswith(("6","9")) else "bj" if code.startswith("8") else "sz"

# ========== 1. 腾讯实时行情 ==========
def collect_tencent_quote(codes):
    """批量获取腾讯实时行情（含PE/PB/市值）"""
    prefixed = [f"{get_prefix(c)}{c}" for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read().decode("gbk")
    result = []
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53: continue
        code = key[2:]
        result.append({
            "stock_code": code, "stock_name": vals[1],
            "price": vals[3] or 0, "pe_ttm": vals[39] or 0,
            "pb": vals[46] or 0, "mcap_yi": vals[44] or 0,
            "turnover_pct": vals[38] or 0, "change_pct": vals[32] or 0,
            "change_amt": vals[31] or 0, "last_close": vals[4] or 0,
            "volume": (float(vals[6]) * 100) if vals[6] else 0,
            "amount_wan": vals[37] or 0,
        })
    return result

# ========== 2. 资金流向（日级）==========
def collect_fund_flow(code):
    """个股资金流向（日级，最近120日）"""
    mk = 1 if code.startswith("6") else 0
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {"secid": f"{mk}.{code}", "fields1": "f1,f2,f3,f7",
              "fields2": "f51,f52,f53,f54,f55,f56,f57", "lmt": "120"}
    try:
        r = em_get(url, params=params, timeout=5)
        if not r or not r.text: return []
        d = r.json()
        if not isinstance(d, dict) or not d.get("data"): return []
        klines = (d.get("data") or {}).get("klines") or []
        if not klines: return []
        rows = []
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 7:
                rows.append({"stock_code": code, "date": parts[0],
                    "main_net": parts[1], "small_net": parts[2],
                    "mid_net": parts[3], "large_net": parts[4], "super_net": parts[5]})
        return rows
    except:
        return []

# ========== 3. 龙虎榜 ==========
def collect_dragon_tiger(trade_date=None):
    """全市场当日龙虎榜"""
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    data = em_datacenter("RPT_DAILYBILLBOARD_DETAILSNEW",
        filter_str=f"(TRADE_DATE>='{trade_date}')(TRADE_DATE<='{trade_date}')",
        page_size=500, sort_columns="BILLBOARD_NET_AMT", sort_types="-1")
    rows = []
    for row in data:
        rows.append({
            "trade_date": str(row.get("TRADE_DATE",""))[:10],
            "stock_code": row.get("SECURITY_CODE",""),
            "stock_name": row.get("SECURITY_NAME_ABBR",""),
            "reason": row.get("EXPLANATION",""),
            "net_buy_wan": round((row.get("BILLBOARD_NET_AMT") or 0)/10000, 1),
            "buy_wan": round((row.get("BILLBOARD_BUY_AMT") or 0)/10000, 1),
            "sell_wan": round((row.get("BILLBOARD_SELL_AMT") or 0)/10000, 1),
            "change_pct": round(float(row.get("CHANGE_RATE") or 0), 2),
        })
    return rows

# ========== 4. 限售解禁 ==========
def collect_lockup(code):
    """限售解禁日历"""
    data = em_datacenter("RPT_LIFT_STAGE", filter_str=f'(SECURITY_CODE="{code}")',
                         page_size=15, sort_columns="FREE_DATE", sort_types="-1")
    rows = []
    for row in data:
        rows.append({
            "stock_code": code,
            "free_date": str(row.get("FREE_DATE",""))[:10],
            "lockup_type": row.get("LIMITED_STOCK_TYPE",""),
            "shares": row.get("FREE_SHARES_NUM", 0),
            "ratio": row.get("FREE_RATIO", 0),
        })
    return rows

# ========== 5. 行业对比 ==========
def collect_industry_compare():
    """东财行业板块涨跌幅排名"""
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {"pn":"1","pz":"100","po":"1","np":"1","fltt":"2","invt":"2",
              "fs":"m:90+t:2","fields":"f2,f3,f4,f12,f14,f104,f105,f128"}
    r = em_get(url, params=params, timeout=10)
    items = (r.json().get("data") or {}).get("diff") or []
    rows = []
    for item in items:
        rows.append({
            "industry": item.get("f14",""),
            "code": item.get("f12",""),
            "change_pct": item.get("f3",0),
            "up_count": item.get("f104",0),
            "down_count": item.get("f105",0),
        })
    return rows

# ========== 6. 概念板块 ==========
def collect_concept_blocks(code):
    """百度概念板块归属"""
    url = f"https://finance.pae.baidu.com/api/getrelatedblock?code={code}&market=ab&typeCode=all&finClientType=pc"
    try:
        r = requests.get(url, headers={"User-Agent":UA}, timeout=10)
        d = r.json()
    except: return []
    rows = []
    for block in d.get("Result",[]):
        bt = block.get("type","")
        for item in block.get("list",[]):
            rows.append({
                "stock_code": code,
                "block_name": item.get("name",""),
                "block_type": "行业" if "行业" in bt else "概念" if "概念" in bt else "地域",
                "change_pct": item.get("increase",""),
            })
    return rows

# ========== 7. 个股新闻 ==========
def collect_stock_news(code, limit=20):
    """东财个股新闻"""
    cb = "jQ"
    inner = json.dumps({"uid":"","keyword":code,"type":["cmsArticleWebOld"],
        "client":"web","clientType":"web","clientVersion":"curr",
        "param":{"cmsArticleWebOld":{"searchScope":"default","sort":"default",
            "pageIndex":1,"pageSize":limit,"preTag":"","postTag":""}}}, separators=(',',':'))
    try:
        r = em_get("https://search-api-web.eastmoney.com/search/jsonp",
            params={"cb":cb,"param":inner}, timeout=10)
        txt = r.text
        js = txt[txt.index("(")+1:txt.rindex(")")]
        d = json.loads(js)
    except: return []
    arts = d.get("result",{}).get("cmsArticleWebOld",[]) or []
    rows = []
    for a in arts:
        rows.append({
            "stock_code": code,
            "title": re.sub(r'<[^>]+>','',a.get("title","")),
            "content": re.sub(r'<[^>]+>','',a.get("content",""))[:200],
            "publish_time": a.get("date",""),
            "source": a.get("mediaName",""),
        })
    return rows

# ========== 8. 公告 ==========
def collect_filings(code, limit=20):
    """巨潮公告"""
    org = f"gssh0{code}" if code.startswith("6") else f"gsbj0{code}" if code.startswith(("8","4")) else f"gssz0{code}"
    payload = {"stock":f"{code},{org}","tabName":"fulltext","pageSize":str(limit),
        "pageNum":"1","column":"","category":"","plate":"","seDate":"","searchkey":"",
        "secid":"","sortName":"","sortType":"","isHLtitle":"true"}
    try:
        r = requests.post("https://www.cninfo.com.cn/new/hisAnnouncement/query",
            data=payload, headers={"User-Agent":UA,"Content-Type":"application/x-www-form-urlencoded",
                "Referer":"https://www.cninfo.com.cn/new/disclosure"}, timeout=15)
        d = r.json() if r.text.strip() else {}
    except Exception as e:
        print(f'  公告请求失败: {e}')
        return []
    rows = []
    for item in d.get("announcements",[]) or []:
        rows.append({
            "stock_code": code,
            "title": item.get("announcementTitle",""),
            "type": item.get("announcementTypeName",""),
            "publish_date": datetime.fromtimestamp(item.get("announcementTime",0)/1000).strftime("%Y-%m-%d"),
        })
    return rows

# ========== 9. 指数行情 + 指数K线 ==========
INDEX_CODES = [
    ('sh000001', '上证指数'), ('sz399001', '深证成指'),
    ('sz399006', '创业板指'), ('sh000688', '科创50'), ('sh000300', '沪深300'),
]

def collect_index_quote():
    """腾讯指数实时行情"""
    codes = [c[0] for c in INDEX_CODES]
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("gbk")
    except:
        return []
    result = []
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 40: continue
        name = None
        for ic, iname in INDEX_CODES:
            if ic.endswith(key):
                name = iname
                break
        result.append({
            "index_code": key, "index_name": name or vals[1],
            "price": vals[3] or 0, "change_pct": vals[32] or 0,
            "open": vals[5] or 0, "high": vals[33] or 0,
            "low": vals[34] or 0, "volume": vals[6] or 0,
            "amount": vals[37] or 0,
        })
    return result

def collect_index_kline(code):
    """腾讯指数日K线（最近120天）"""
    prefix = "sh" if code.startswith(("0","6","9")) else "sz"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,120,qfq"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        d = r.json()
    except:
        return []
    data = d.get("data", {})
    klines = (data.get(code) or data.get(prefix + code) or {}).get("day", [])
    if not klines:
        klines = data.get("qt", {}).get(code, {}).get("day", [])
    rows = []
    for k in klines:
        if len(k) >= 6:
            rows.append({
                "index_code": code,
                "trade_date": k[0].replace("-", ""),
                "open": k[1], "close": k[2], "high": k[3],
                "low": k[4], "volume": k[5] if len(k) > 5 else 0,
                "amount": k[6] if len(k) > 6 else 0,
                "change_pct": round((float(k[2]) - float(k[1])) / float(k[1]) * 100, 2) if float(k[1]) > 0 else 0,
            })
    return rows

# ========== 10. 股票行业归属（从 Tencent 查询） ==========
def collect_stock_industries(codes):
    """从腾讯批量获取股票行业"""
    all_rows = []
    for batch_start in range(0, len(codes), 100):
        batch = codes[batch_start:batch_start+100]
        prefixed = [f"{'sh' if c.startswith(('6','9')) else 'bj' if c.startswith('8') else 'sz'}{c}" for c in batch]
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read().decode("gbk")
        except:
            time.sleep(0.5)
            continue
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            vals = line.split('"')[1].split("~")
            if len(vals) < 45: continue
            code = vals[2]
            industry = vals[43] if len(vals) > 43 else ""
            if industry and industry.strip():
                all_rows.append({
                    "stock_code": code, "industry": industry,
                    "industry_en": "",
                })
        time.sleep(0.5)
    return all_rows

# ========== 主采集流程 ==========
def main():
    print(f'=== 全市场数据采集启动 {datetime.now():%H:%M:%S} ===\n')

    # 0. 从 CSV 读取股票列表（Hive fallback）
    stocks = []
    try:
        import glob
        sbfiles = sorted(glob.glob('/data/raw/stock_basic_*.csv'))
        if sbfiles:
            with open(sbfiles[-1], 'r', encoding='utf-8-sig') as f:
                import csv
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get('stock_code', row.get('code', ''))
                    name = row.get('stock_name', row.get('name', ''))
                    if code: stocks.append({'code': code, 'name': name})
            print(f'从 CSV 读取 {len(stocks)} 只股票')
    except Exception as e:
        print(f'CSV读取失败: {e}')
    if not stocks:
        try:
            sys.path.insert(0, '/app/pylib')
            from pyhive import hive
            conn = hive.connect(host='hive-server', port=10000, timeout=10)
            c = conn.cursor()
            c.execute("SELECT stock_code, stock_name FROM stock_basic ORDER BY stock_code")
            stocks = [{'code': r[0], 'name': r[1]} for r in c.fetchall()]
            conn.close()
            print(f'从 Hive 读取 {len(stocks)} 只股票')
        except Exception as e:
            print(f'Hive连接失败: {e}')
            return

    codes = [s['code'] for s in stocks]

    # 1. 腾讯实时行情（用于 stock_detail / 指数）
    print('\n1. 采集腾讯实时行情...')
    all_quotes = []
    for batch_start in range(0, len(codes), 100):
        all_quotes.extend(collect_tencent_quote(codes[batch_start:batch_start+100]))
        time.sleep(0.5)
    save_csv('tencent_quote', all_quotes)

    # 2. 资金流向（全部股票，每只120日）
    print('\n2. 采集个股资金流向...')
    all_flow = []
    for i, code in enumerate(codes):
        rows = collect_fund_flow(code)
        if rows:
            all_flow.extend(rows)
        if (i+1) % 500 == 0:
            print(f'   进度: {i+1}/{len(codes)}, 已采集{len(all_flow)}条')
        time.sleep(0.05)
    save_csv('fund_flow', all_flow)

    # 3. 龙虎榜
    print('\n3. 采集全市场龙虎榜...')
    dt = collect_dragon_tiger()
    save_csv('dragon_tiger', dt)

    # 4. 行业对比
    print('\n4. 采集行业板块排名...')
    ind = collect_industry_compare()
    save_csv('industry_compare', ind)

    # 5. 概念板块（全部股票）
    print('\n5. 采集概念板块归属...')
    all_cb = []
    for i, code in enumerate(codes):
        rows = collect_concept_blocks(code)
        if rows:
            all_cb.extend(rows)
        if (i+1) % 500 == 0:
            print(f'   进度: {i+1}/{len(codes)}')
        time.sleep(0.05)
    save_csv('concept_blocks', all_cb)

    # 6. 限售解禁（全部股票）
    print('\n6. 采集限售解禁...')
    all_lu = []
    for i, code in enumerate(codes):
        rows = collect_lockup(code)
        if rows:
            all_lu.extend(rows)
        if (i+1) % 500 == 0:
            print(f'   进度: {i+1}/{len(codes)}')
        time.sleep(0.1)
    save_csv('lockup', all_lu)

    # 7. 个股新闻（全部股票）
    print('\n7. 采集个股新闻...')
    all_news = []
    for i, code in enumerate(codes):
        if i > 2000: break  # 新闻API较慢，先采集前2000只
        rows = collect_stock_news(code)
        if rows:
            all_news.extend(rows)
        if (i+1) % 500 == 0:
            print(f'   进度: {i+1}/{len(codes)}, 已采集{len(all_news)}条')
        time.sleep(0.3)
    save_csv('stock_news', all_news)

    # 8. 公告（全部股票）
    print('\n8. 采集巨潮公告...')
    all_f = []
    for i, code in enumerate(codes):
        rows = collect_filings(code)
        if rows:
            all_f.extend(rows)
        if (i+1) % 20 == 0:
            print(f'   进度: {i+1}/{len(codes)}')
        time.sleep(0.3)
    save_csv('filings', all_f)

    # 9. 指数行情 + 指数K线
    print('\n9. 采集指数行情...')
    idx_q = collect_index_quote()
    save_csv('tencent_index', idx_q)
    print('\n10. 采集指数K线...')
    all_idx_k = []
    for ic, _ in INDEX_CODES:
        klines = collect_index_kline(ic)
        if klines:
            all_idx_k.extend(klines)
            print(f'   {ic}: {len(klines)}天')
        time.sleep(0.3)
    save_csv('index_daily', all_idx_k)

    # 11. 股票行业归属
    print('\n11. 采集股票行业归属...')
    inds = collect_stock_industries(codes)
    save_csv('stock_industry', inds)

    print(f'\n=== 采集完成 {datetime.now():%H:%M:%S} ===')
    print(f'  总计保存 {len(os.listdir(CSV_DIR))} 个CSV文件')

if __name__ == '__main__':
    main()
