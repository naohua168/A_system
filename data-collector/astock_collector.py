"""
A股全栈数据采集器（集成 a-stock-data 方法）
采集缺失数据 → CSV → HDFS → Hive → Redis → 前端
"""
import requests, json, time, re, csv, os, sys, random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path('/data/raw')
EM_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://data.eastmoney.com/",
}
THS_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

def _save_csv(prefix: str, rows: list, fieldnames: list):
    """保存到 /data/raw/{prefix}_{timestamp}.csv"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = DATA_DIR / f"{prefix}_{ts}.csv"
    with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  ✅ {fp.name}: {len(rows)}行")

def get_stock_codes():
    """从现有 stock_basic CSV 获取股票代码"""
    files = sorted(DATA_DIR.glob('stock_basic_*.csv'))
    if not files:
        print("  ⚠️ stock_basic CSV 不存在")
        return []
    codes = []
    with open(files[0], 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('code', '').strip()
            if code:
                codes.append(code)
    return codes[:2000]  # 全市场

# ========== 信号层 ==========

def em_get(url, params=None):
    """东财接口统一入口（带限流）"""
    time.sleep(1.1 + random.random())
    return requests.get(url, params=params, headers=EM_HEADERS, timeout=15)

def collect_dragon_tiger(date=None):
    """龙虎榜 — 东财 datacenter"""
    if not date: date = datetime.now().strftime("%Y-%m-%d")
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "TRADE_DATE", "sortTypes": "-1", "pageSize": 100, "pageNumber": 1,
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW", "columns": "ALL",
        "filter": f'(TRADE_DATE=\'{date}\')',
    }
    try:
        r = em_get(url, params); d = r.json()
        items = d.get('result', {}).get('data', [])
        rows = [{
            'stock_code': i.get('SECUCODE','')[:6], 'stock_name': i.get('SECURITY_NAME',''),
            'trade_date': i.get('TRADE_DATE',''), 'reason': i.get('BOARD_REASON',''),
            'buy_amount': i.get('BUY_AMOUNT',0), 'sell_amount': i.get('SELL_AMOUNT',0),
            'net_amount': i.get('NET_AMOUNT',0),
        } for i in items if i.get('SECUCODE')]
        if rows:
            _save_csv('dragon_tiger', rows, ['stock_code','stock_name','trade_date','reason','buy_amount','sell_amount','net_amount'])
        return rows
    except Exception as e:
        print(f"  ⚠️ dragon_tiger: {e}")
        return []

def collect_northbound():
    """北向资金 — 同花顺 HTTP"""
    url = "https://push2.eastmoney.com/api/qt/kamt.kamtget"
    params = {"fields1": "f1,f2,f3,f4", "fields2": "f51,f52,f53,f54,f55,f56", "kamt": "1"}
    try:
        r = em_get(url, params); d = r.json()
        data = d.get('data', {})
        hgt = data.get('hgt', {}) or {}
        sgt = data.get('sgt', {}) or {}
        rows = [{
            'trade_date': datetime.now().strftime("%Y-%m-%d"),
            'hgt_yi': hgt.get('f52', 0), 'sgt_yi': sgt.get('f52', 0),
        }]
        _save_csv('northbound', rows, ['trade_date','hgt_yi','sgt_yi'])
        return rows
    except Exception as e:
        print(f"  ⚠️ northbound: {e}")
        return []

# ========== 资金面 ==========

def collect_fund_flow(code):
    """120日资金流向 — 东财 push2"""
    url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    params = {"secid": f"1.{code}" if code.startswith('6') else f"0.{code}",
              "fields1": "f1,f2,f3,f7", "fields2": "f51,f52,f53,f54,f55",
              "klt": "101", "lmt": "120"}
    try:
        r = em_get(url, params); d = r.json()
        klinedata = d.get('data', {}).get('klinedata', [])
        rows = [{'date': i['f51'], 'close': i['f52'], 'main_net': i['f53'],
                 'super_net': 0, 'large_net': 0, 'mid_net': 0, 'small_net': 0}
                for i in klinedata if i.get('f51')]
        if rows:
            _save_csv(f'fund_flow_{code}', rows, ['date','close','main_net','super_net','large_net','mid_net','small_net'])
        return rows
    except:
        return []

def collect_lockup():
    """限售解禁 — 东财 datacenter"""
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "sortColumns": "LATEST_DATE", "sortTypes": "1", "pageSize": 100, "pageNumber": 1,
        "reportName": "RPT_LOCKUP_LOCKUP", "columns": "ALL",
        "filter": "",
    }
    try:
        r = em_get(url, params); d = r.json()
        items = d.get('result', {}).get('data', [])
        rows = [{
            'stock_code': i.get('SECURITY_CODE',''), 'stock_name': i.get('SECURITY_NAME',''),
            'lockup_date': i.get('LATEST_DATE',''), 'lockup_type': i.get('LOCKUP_TYPE',''),
            'shares': i.get('UNLOCK_SHARES',0), 'float_ratio': i.get('FLOAT_RATIO',0),
        } for i in items if i.get('SECURITY_CODE')]
        if rows:
            _save_csv('lockup', rows, ['stock_code','stock_name','lockup_date','lockup_type','shares','float_ratio'])
        return rows
    except Exception as e:
        print(f"  ⚠️ lockup: {e}")
        return []

# ========== 研报层 ==========

def collect_research(code):
    """研报 — 东财 reportapi"""
    url = "https://reportapi.eastmoney.com/report/list"
    params = {"cb": "jQuery", "pageNo": "1", "pageSize": "20",
              "code": f"1{code}" if code.startswith('6') else f"0{code}",
              "industryCode": "", "industryAll": "", "reportType": "1"}
    try:
        r = requests.get(url, params=params, headers=EM_HEADERS, timeout=10)
        text = r.text
        # 去掉 JSONP 包裹
        if '(' in text and text.endswith(')'):
            text = text[text.index('(')+1:-1]
        d = json.loads(text)
        items = d.get('data', [])
        rows = [{
            'stock_code': code, 'org_name': i.get('orgName',''),
            'title': i.get('title',''), 'publish_date': i.get('publishDate',''),
            'rating': i.get('emRating',''), 'target_price': i.get('targetPrice',0),
        } for i in items if i.get('title')]
        if rows:
            _save_csv(f'research_{code}', rows, ['stock_code','org_name','title','publish_date','rating','target_price'])
        return rows
    except:
        return []

def collect_eps_forecast(code):
    """一致预期EPS — 同花顺 iwencai"""
    url = "https://www.iwencai.com/stockpick/cache"
    data = {"question": f"({code})一致预期每股收益"}
    try:
        r = requests.post(url, json=data, headers=THS_HEADERS, timeout=15)
        d = r.json()
        rows = [{'stock_code': code, 'year': '2026', 'eps': d.get('data',[{}])[0].get('d',0) if d.get('data') else 0}]
        _save_csv(f'eps_{code}', rows, ['stock_code','year','eps'])
        return rows
    except:
        return []

# ========== 资讯层 ==========

def collect_stock_news(code):
    """个股新闻 — 东财"""
    url = "https://push2.eastmoney.com/api/qt/stock/amuselive/news/get"
    params = {"secid": f"1.{code}" if code.startswith('6') else f"0.{code}", "lmt": "5"}
    try:
        r = em_get(url, params); d = r.json()
        items = d.get('data', {}).get('items', [])
        rows = [{'stock_code': code, 'title': i.get('title','').replace('<em>','').replace('</em>',''),
                 'content': i.get('content',''), 'publish_time': i.get('showtime','')}
                for i in items if i.get('title')]
        if rows:
            _save_csv(f'news_{code}', rows, ['stock_code','title','content','publish_time'])
        return rows
    except:
        return []

# ========== 主流程 ==========

def collect_all():
    print(f'\n{"="*50}')
    print(f'📦 a-stock 全量采集 [{datetime.now():%H:%M:%S}]')
    print(f'{"="*50}')

    # 全局信号
    collect_dragon_tiger()
    collect_northbound()

    # 逐股采集
    codes = get_stock_codes()
    print(f'逐股采集: {len(codes)} 只股票')
    for i, code in enumerate(codes):
        if i % 100 == 0:
            print(f'  [{i}/{len(codes)}]')
        collect_lockup()  # 全局数据只采一次
        collect_fund_flow(code)
        collect_stock_news(code)
        if i < 50:  # 研报仅前50只（较慢）
            collect_research(code)
            collect_eps_forecast(code)
        time.sleep(0.3)

    print(f'✅ a-stock 采集完成 [{datetime.now():%H:%M:%S}]')

if __name__ == '__main__':
    # 检查依赖
    for mod in ['requests']:
        __import__(mod)
    collect_all()
