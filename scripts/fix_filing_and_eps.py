#!/usr/bin/env python3
"""
修复3项: 公告(filing) + 一致预期(consensus_eps) + 热点股票新闻
"""
import os, time, logging, requests, pymysql, json, re
from datetime import datetime
import pandas as pd
from io import StringIO

os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4')
# 注意: 不用autocommit，用显式commit批量提交
cur = conn.cursor()
sess = requests.Session(); sess.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

# ====== 1. 公告采集 (info_filing) ======
log.info("=== 公告采集 ===")
cur.execute("SELECT COUNT(*) FROM info_filing")
before = cur.fetchone()[0]
log.info(f"当前: {before} 条")

# 获取已有数据的股票，用于增量跳过
cur.execute("SELECT DISTINCT stock_code FROM info_filing")
existing_filing_codes = set(r[0] for r in cur.fetchall())
log.info(f"已有公告股票: {len(existing_filing_codes)} 只")

if before < 100:
    cur.execute("SELECT stock_code, stock_name FROM stock ORDER BY total_market_cap DESC LIMIT 1000")
    top_stocks = cur.fetchall()
    log.info(f"采集TOP1000市值股票公告（已有{len(existing_filing_codes)}只跳过）...")
    
    inserted = 0
    skipped = 0
    for i, (code, name) in enumerate(top_stocks):
        # 增量跳过：已有数据的股票不再采集
        if code in existing_filing_codes:
            skipped += 1
            continue
        try:
            org_id = f"gssh0{code}" if code.startswith('6') else (f"gsbj0{code}" if code.startswith(('8','4')) else f"gssz0{code}")
            r = sess.post("https://www.cninfo.com.cn/new/hisAnnouncement/query",
                data={"stock":f"{code},{org_id}","tabName":"fulltext","pageSize":"30","pageNum":"1",
                      "column":"szse","sortName":"","sortType":"","isHLtitle":"true"},
                headers={"User-Agent":UA,"Content-Type":"application/x-www-form-urlencoded",
                         "Referer":"https://www.cninfo.com.cn/new/disclosure",
                         "Origin":"https://www.cninfo.com.cn"}, timeout=15)
            anns = r.json().get("announcements") or []
            for ann in anns:
                atime = ann.get("announcementTime")
                fd = datetime.fromtimestamp(atime/1000).strftime("%Y-%m-%d") if isinstance(atime,(int,float)) else str(atime)[:10]
                cur.execute("INSERT INTO info_filing(stock_code,stock_name,title,filing_date,category,url) VALUES(%s,%s,%s,%s,%s,%s)",
                    (code, name, ann.get("announcementTitle","")[:500], fd,
                     ann.get("announcementTypeName","") or "", 
                     f"https://www.cninfo.com.cn/new/disclosure/detail?annoId={ann.get('announcementId','')}"))
                inserted += 1
        except: pass
        if (i+1)%100==0: log.info(f"  公告进度:{i+1}/1000 (跳过{skipped}), 新增插入:{inserted}")
        time.sleep(0.05)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM info_filing")
    log.info(f"公告完成: {cur.fetchone()[0]} 条 (跳过{skipped}只已有股票)")

# ====== 2. 一致预期采集 (info_consensus_eps) ======
log.info("\n=== 一致预期采集 ===")
cur.execute("SELECT COUNT(DISTINCT stock_code) FROM info_consensus_eps")
before = cur.fetchone()[0]

# 获取已有数据的股票，用于增量跳过
cur.execute("SELECT DISTINCT stock_code FROM info_consensus_eps")
existing_eps_codes = set(r[0] for r in cur.fetchall())
log.info(f"已有一致预期股票: {len(existing_eps_codes)} 只")

# 获取热门+高关注度股票
cur.execute("""
    SELECT DISTINCT s.stock_code FROM stock s
    JOIN signal_dragon_tiger_detail d ON s.stock_code = d.stock_code
    UNION SELECT DISTINCT s.stock_code FROM stock s WHERE s.total_market_cap > 50000000000
    UNION SELECT stock_code FROM info_consensus_eps
    ORDER BY stock_code
""")
eps_stocks = [r[0] for r in cur.fetchall()[:400]]
log.info(f"采集候选 {len(eps_stocks)} 只股票一致预期...")

inserted = 0
skipped = 0
for i, code in enumerate(eps_stocks):
    # 增量跳过：已有数据的股票不再重新采集
    if code in existing_eps_codes:
        skipped += 1
        if (i+1)%100==0: log.info(f"  EPS跳过:{i+1}/{len(eps_stocks)}, 已跳过{skipped}, 新增{inserted}")
        continue
    try:
        r = sess.get(f"https://basic.10jqka.com.cn/new/{code}/worth.html",
                     headers={"User-Agent":UA}, timeout=10)
        r.encoding = "gbk"
        tables = pd.read_html(StringIO(r.text))
        
        for t in tables:
            cols = [str(c) for c in t.columns]
            if any("每股收益" in c or "均值" in c for c in cols):
                for _, row in t.iterrows():
                    try:
                        year_val = row.iloc[0]
                        year = int(float(str(year_val))) if str(year_val).replace('.','').isdigit() else None
                        if year and 2024 <= year <= 2030:
                            count = int(float(row.iloc[1])) if len(row)>1 and str(row.iloc[1]).replace('.','').isdigit() else None
                            avg = float(row.iloc[3]) if len(row)>3 else None
                            mn = float(row.iloc[2]) if len(row)>2 else None
                            mx = float(row.iloc[4]) if len(row)>4 else None
                            
                            cur.execute("""
                                INSERT INTO info_consensus_eps(stock_code, year, forecast_count, avg_eps, min_eps, max_eps)
                                VALUES(%s,%s,%s,%s,%s,%s)
                                ON DUPLICATE KEY UPDATE forecast_count=VALUES(forecast_count),
                                    avg_eps=VALUES(avg_eps), min_eps=VALUES(min_eps), max_eps=VALUES(max_eps)
                            """, (code, year, count, avg, mn, mx))
                            inserted += 1
                    except: pass
                break
    except: pass
    if (i+1)%100==0: log.info(f"  EPS进度:{i+1}/{len(eps_stocks)} (跳过{skipped}), 新增插入:{inserted}")
    time.sleep(0.15)
conn.commit()

# ====== 3. 扩展个股新闻 (info_stock_news) - 尝试备用API ======
log.info("\n=== 个股新闻 ===")
cur.execute("SELECT COUNT(DISTINCT stock_code) FROM info_stock_news")
before = cur.fetchone()[0]

# 尝试cls.cn财联社API（跟a-stock-data库）
try:
    r = sess.get("https://www.cls.cn/nodeapi/telegraphList", 
                 params={"rn":"50","page":"1"},
                 headers={"User-Agent":UA,"Referer":"https://www.cls.cn/"}, timeout=10)
    data = r.json()
    items = data.get("data",{}).get("roll_data",[]) or []
    log.info(f"财联社快讯: {len(items)} 条")
    inserted = 0
    for item in items:
        t = item.get("ctime","")
        cur.execute("""
            INSERT IGNORE INTO info_cls_news(stock_code, title, content_summary, publish_time, source, url)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, ("000000", item.get("title","")[:200], (item.get("content","") or item.get("brief",""))[:500], t, "财联社", ""))
        inserted += cur.rowcount
    conn.commit()
    log.info(f"财联社插入: {inserted}")
except Exception as e:
    log.warning(f"财联社失败: {e}")

# ====== 最终统计 ======
log.info("\n=== 最终统计 ===")
for t, label in [("info_filing","公告"), ("info_consensus_eps","一致预期"), ("info_stock_news","个股新闻"), ("info_cls_news","财联社")]:
    cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM {t}")
    c, s = cur.fetchone()
    log.info(f"{label}: {c}条/{s}只")

conn.close()
log.info("完成!")
