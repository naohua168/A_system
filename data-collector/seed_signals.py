#!/usr/bin/env python3
"""信号层数据播种（后台运行）：锁解+一致预期+资金流向"""
import json, subprocess, urllib.request, urllib.parse, time
from datetime import date, timedelta

UA = 'Mozilla/5.0'

def rset(key, val, ttl=3600):
    subprocess.run(['redis-cli', '-h', 'redis', 'SETEX', key, str(ttl),
        json.dumps(val, ensure_ascii=False)], capture_output=True, timeout=10)

def rget(key):
    r = subprocess.run(['redis-cli', '-h', 'redis', 'GET', key], capture_output=True, timeout=10)
    return json.loads(r.stdout) if r.stdout else None

today = date.today().strftime('%Y-%m-%d')

# 1. 锁解 - 全市场未来90天待解禁
filter_str = urllib.parse.quote(f"(FREE_DATE>='{today}')(FREE_DATE<='{(date.today()+timedelta(90)).strftime(\"%Y-%m-%d\")}')")
try:
    req = urllib.request.Request(
        f'https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LIFT_STAGE&columns=ALL&pageSize=500&sortColumns=FREE_DATE&sortTypes=1&filter={filter_str}',
        headers={'User-Agent': UA, 'Referer': 'https://data.eastmoney.com/'})
    items = json.loads(urllib.request.urlopen(req, timeout=15).read().decode()).get('result',{}).get('data',[])
    seen=set(); rows=[]
    for item in items:
        c=item.get('SECURITY_CODE','')
        if not c or c in seen: continue
        seen.add(c)
        sw=float(item.get('CURRENT_FREE_SHARES',0) or 0)
        rows.append({'stockCode':c,'stockName':item.get('SECURITY_NAME_ABBR',''),
            'lockupDate':str(item.get('FREE_DATE',''))[:10],
            'lockupType':str(item.get('FREE_SHARES_TYPE','') or ''),
            'shares':int(sw*10000),
            'floatRatio':round(float(item.get('FREE_RATIO',0) or 0)*100,2),
            'typeTag':'upcoming'})
    rset('market:lockup_upcoming', rows)
    print(f'Lockup: {len(rows)}')
except Exception as e: print(f'Lockup: {e}')

# 2. 一致预期 - 按报告发布年份正确映射
hot_stocks = rget('market:stock_basic')
hot_codes = [s['stock_code'] for s in (hot_stocks or []) if s.get('stock_code')][:10]
for code in hot_codes:
    try:
        params = f'pageSize=50&pageNo=1&qType=0&code={code}&industryCode=*&industry=*&rating=*&ratingChange=*&beginTime=2000-01-01&endTime=2030-01-01'
        req = urllib.request.Request(f'https://reportapi.eastmoney.com/report/list?{params}',
            headers={'User-Agent': UA, 'Referer': 'https://data.eastmoney.com/'})
        reports = json.loads(urllib.request.urlopen(req, timeout=10).read().decode()).get('data', [])
        if not reports: continue
        years = {}
        for r in reports:
            py = int((r.get('publishDate','') or '')[:4])
            if not py: continue
            for fld, off in [('predictThisYearEps',0),('predictNextYearEps',1),('predictNextTwoYearEps',2)]:
                v = r.get(fld)
                if v and v != '-':
                    yr = str(py+off)
                    years.setdefault(yr,[]).append(float(v))
        rows = [{'year':yr,'forecastCount':len(vals),'minEps':round(min(vals),3),
                 'avgEps':round(sum(vals)/len(vals),3),'maxEps':round(max(vals),3),'stockCode':code}
                for yr,vals in sorted(years.items()) if len(vals)>=2]
        if rows: rset(f'market:consensus_eps_{code}', rows)
        time.sleep(0.3)
    except: pass

# 3. 资金流向 - 仅尝试热门股
for code in ['000858','600519','688017','300750','002594','300059','000001','002415','002475','300124']:
    try:
        m = 1 if code.startswith(('6','9')) else 0
        url = f'https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?secid={m}.{code}&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57&lmt=20'
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://quote.eastmoney.com/'})
        resp = urllib.request.urlopen(req, timeout=10)
        klines = json.loads(resp.read().decode()).get('data',{}).get('klines',[])
        rows = []
        for line in klines:
            parts = line.split(',')
            if len(parts)>=7:
                rows.append({'tradeDate':parts[0],'close':float(parts[6]) if parts[6] not in ('-','') else 0,
                    'mainIn':float(parts[1]) if parts[1] not in ('-','') else 0,
                    'superNetIn':float(parts[5]) if parts[5] not in ('-','') else 0,
                    'largeNetIn':float(parts[4]) if parts[4] not in ('-','') else 0,
                    'mediumNetIn':float(parts[3]) if parts[3] not in ('-','') else 0,
                    'smallNetIn':float(parts[2]) if parts[2] not in ('-','') else 0})
        if rows:
            rset(f'market:fund_flow_{code}', rows)
        time.sleep(2)
    except:
        time.sleep(3)
