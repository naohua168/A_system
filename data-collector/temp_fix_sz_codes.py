#!/usr/bin/env python3
"""为 000001 加载K线数据到 stock_daily"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import sys, time, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
import requests
import pymysql

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger("fix_000001")

CODES = ["000001","000002","000333","002415","002594","000725","002475","000858","002142","002230","002736","002304"]

sess = requests.Session()
sess.trust_env = False

def get_prefix(code):
    return {"6":"sh","5":"sh","9":"sh","0":"sz","3":"sz","2":"sz","4":"bj","8":"bj"}.get(code[0], "sh")

def fetch(code, days=500):
    prefix = get_prefix(code)
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{days},qfq"
    try:
        r = sess.get(url, timeout=15, proxies={"http":None,"https":None})
        data = r.json()
        if not data or data.get("error"): return []
        klines = (data.get("data",{}).get(f"{prefix}{code}",{}).get("day",[]) or
                  data.get("data",{}).get(f"{prefix}{code}",{}).get("qfqday",[]))
        return klines
    except Exception as e:
        log.warning(f"  {code} error: {e}")
        return []

conn = pymysql.connect(host="localhost", port=3307, user="root", password="hadoop123", database="stock_analysis",
                       charset="utf8mb4", autocommit=False)
cur = conn.cursor()

for code in CODES:
    log.info(f"采集 {code}...")
    klines = fetch(code)
    if not klines or len(klines) < 5:
        log.warning(f"  {code} 无数据")
        time.sleep(0.3)
        continue
    rows = []
    for k in klines:
        if len(k) < 6: continue
        ds = str(k[0]).replace("-","")
        try:
            rows.append((code, ds, float(k[1]), float(k[2]), float(k[4]), float(k[3]),
                         0.0, int(float(k[5])) if k[5] else 0, 0.0, 0.0, 0.0))
        except: continue
    cur.executemany("""INSERT IGNORE INTO stock_daily
        (stock_code,trade_date,open_price,high_price,low_price,close_price,pre_close,volume,amount,change_percent,turnover_rate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    conn.commit()
    log.info(f"  ✅ {code}: {len(rows)} 条 (最新: {klines[-1][0]})")
    time.sleep(0.3)

# Fix change_percent
cur.execute("""
    UPDATE stock_daily t1 JOIN stock_daily t2 ON t1.stock_code=t2.stock_code
        AND t2.trade_date=DATE_SUB(t1.trade_date,INTERVAL 1 DAY)
    SET t1.change_percent=ROUND((t1.close_price-t2.close_price)/t2.close_price*100,2),
        t1.pre_close=t2.close_price
    WHERE t1.change_percent=0 AND t1.pre_close=0""")
conn.commit()

cur.execute("SELECT COUNT(*), MAX(trade_date), MIN(trade_date), COUNT(DISTINCT stock_code) FROM stock_daily")
r = cur.fetchone()
log.info(f"stock_daily 总计: {r[1]} ~ {r[2]}, {r[0]} 条, {r[3]} 只")
cur.close()
conn.close()
