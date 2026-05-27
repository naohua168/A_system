#!/usr/bin/env python3
"""
修复: 一致预期(正确列名) + 个股新闻(多源)
"""
import os, time, logging, requests, pymysql, re, json
import pandas as pd; from io import StringIO

os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4')
cur = conn.cursor()
sess = requests.Session(); sess.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

# ====== 1. 一致预期 (info_consensus_eps) ======
log.info("=== 一致预期 ===")
cur.execute("SELECT COUNT(DISTINCT stock_code) FROM info_consensus_eps")
before = cur.fetchone()[0]

# 获取高市值+龙虎榜+研报覆盖的股票
cur.execute("""
    SELECT DISTINCT s.stock_code FROM stock s
    JOIN signal_dragon_tiger_detail d ON s.stock_code = d.stock_code
    UNION SELECT DISTINCT s.stock_code FROM stock s WHERE s.total_market_cap > 50000000000
    UNION SELECT DISTINCT stock_code FROM info_research_report
    ORDER BY stock_code
""")
target_stocks = [r[0] for r in cur.fetchall()[:500]]
log.info(f"目标: {len(target_stocks)} 只")

inserted = updated = 0
for i, code in enumerate(target_stocks):
    try:
        r = sess.get(f"https://basic.10jqka.com.cn/new/{code}/worth.html",
                     headers={"User-Agent": UA}, timeout=10)
        r.encoding = "gbk"
        tables = pd.read_html(StringIO(r.text))
        
        for t in tables:
            cols = [str(c) for c in t.columns]
            if any("每股收益" in c or "均值" in c for c in cols):
                for _, row in t.iterrows():
                    try:
                        year_val = row.iloc[0]
                        year = int(float(year_val)) if year_val else None
                        if not year or year < 2024 or year > 2030: continue
                        
                        cnt = int(float(row.iloc[1])) if len(row)>1 and pd.notna(row.iloc[1]) else None
                        avg = float(row.iloc[3]) if len(row)>3 and pd.notna(row.iloc[3]) else None
                        mn = float(row.iloc[2]) if len(row)>2 and pd.notna(row.iloc[2]) else None
                        mx = float(row.iloc[4]) if len(row)>4 and pd.notna(row.iloc[4]) else None
                        
                        if avg:
                            cur.execute("""
                                INSERT INTO info_consensus_eps(stock_code, year, forecast_count, eps, min_eps, max_eps)
                                VALUES(%s,%s,%s,%s,%s,%s)
                                ON DUPLICATE KEY UPDATE
                                    forecast_count=VALUES(forecast_count),
                                    eps=VALUES(eps), min_eps=VALUES(min_eps), max_eps=VALUES(max_eps)
                            """, (code, year, cnt, avg, mn, mx))
                            if cur.rowcount == 1: inserted += 1
                            else: updated += 1
                    except: pass
                break
    except: pass
    if (i+1)%100==0: log.info(f"  EPS: {i+1}/{len(target_stocks)} 新{inserted} 更{updated}")
    time.sleep(0.12)
conn.commit()

cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_consensus_eps")
c, s = cur.fetchone()
log.info(f"一致预期完成: {c}条/{s}只 (新增{inserted}, 更新{updated})")

# ====== 2. 个股新闻 (多API源) ======
log.info("\n=== 个股新闻 ===")
cur.execute("SELECT COUNT(DISTINCT stock_code) FROM info_stock_news")
before = cur.fetchone()[0]

# 2a. 同花顺新闻/公告解析
news_inserted = 0
for code in target_stocks[:200]:  # 只采集前200只避免太慢
    try:
        r = sess.get(f"https://basic.10jqka.com.cn/new/{code}/xw.html",
                     headers={"User-Agent": UA}, timeout=10)
        r.encoding = "gbk"
        # 提取新闻标题
        titles = re.findall(r'<a[^>]*title="([^"]*)"[^>]*>', r.text)
        for title in titles[:5]:
            title_clean = re.sub(r'<[^>]+>','',title).strip()
            if title_clean and len(title_clean) > 10:
                cur.execute("""
                    INSERT IGNORE INTO info_stock_news(stock_code, title, source, publish_time)
                    VALUES(%s,%s,%s,NOW())
                """, (code, title_clean[:500], "同花顺"))
                news_inserted += cur.rowcount
    except: pass
    time.sleep(0.1)
conn.commit()
log.info(f"同花顺新闻: 插入{news_inserted}")

# 2b. 东财全球资讯 (批量拉取)
log.info("东财全球资讯...")
try:
    r = sess.get("https://np-weblist.eastmoney.com/comm/web/getFastNewsList",
        params={"client":"web","biz":"web_724","fastColumn":"102","pageSize":"100","req_trace":str(time.time())},
        headers={"User-Agent":UA,"Referer":"https://kuaixun.eastmoney.com/"}, timeout=10)
    data = r.json()
    items = (data.get("data") or {}).get("fastNewsList", []) or []
    for item in items:
        cur.execute("""
            INSERT IGNORE INTO info_global_news(title, content_summary, publish_time, source)
            VALUES(%s,%s,%s,%s)
        """, (item.get("title","")[:500], item.get("summary","")[:500], item.get("showTime",""), "东财"))
        news_inserted += cur.rowcount
    conn.commit()
    log.info(f"全球资讯: {len(items)}条")
except Exception as e:
    log.warning(f"全球资讯: {e}")

# ====== 统计 ======
log.info("\n=== 最终统计 ===")
cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_consensus_eps")
log.info(f"一致预期: {cur.fetchone()[0]}条/{cur.fetchone()[1]}只")
cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_stock_news")
log.info(f"个股新闻: {cur.fetchone()[0]}条/{cur.fetchone()[1]}只")
cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_filing")
log.info(f"公告: {cur.fetchone()[0]}条/{cur.fetchone()[1]}只")

conn.close()
log.info("完成!")
