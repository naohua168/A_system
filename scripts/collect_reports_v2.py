#!/usr/bin/env python3
"""采集研报(修正列名) + 个股新闻"""
import os, time, logging, requests, pymysql, json, re

os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# 获取热点股票（龙虎榜+新闻+一致预期+龙头）
cur.execute("""
    SELECT DISTINCT s.stock_code, s.stock_name FROM stock s 
    JOIN signal_dragon_tiger_detail d ON s.stock_code = d.stock_code
    UNION SELECT DISTINCT stock_code, '' FROM info_stock_news
    UNION SELECT DISTINCT stock_code, '' FROM info_consensus_eps
    UNION SELECT s.stock_code, s.stock_name FROM stock s WHERE s.total_market_cap > 100000000000
    ORDER BY stock_code
""")
hot_stocks = [(r[0], r[1] or '') for r in cur.fetchall()[:600]]
log.info(f"热门股票: {len(hot_stocks)} 只")

sess = requests.Session(); sess.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

total_reports = 0
total_news = 0

for i, (code, name) in enumerate(hot_stocks):
    # === 研报 ===
    try:
        r = sess.get("https://reportapi.eastmoney.com/report/list",
            params={"code": code, "pageSize": "20", "beginTime": "2025-01-01",
                    "endTime": "2026-12-31", "pageNo": "1", "qType": "0"},
            headers={"User-Agent": UA, "Referer": "https://data.eastmoney.com/"}, timeout=15)
        for row in (r.json().get("data") or []):
            try:
                pd = (row.get("publishDate") or "")[:10]
                cur.execute("""
                    INSERT IGNORE INTO info_research_report
                    (stock_code, stock_name, title, rating, publish_date, org_name, 
                     eps_this_year, eps_next_year, url)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (code, name or row.get("stockName",""), row.get("title","")[:500],
                      row.get("emRatingName","")[:50], pd, row.get("orgSName","")[:200],
                      row.get("predictThisYearEps"), row.get("predictNextYearEps"),
                      f"https://pdf.dfcfw.com/pdf/H3_{row.get('infoCode','')}_1.pdf"))
                total_reports += cur.rowcount
            except: pass
    except: pass

    # === 个股新闻 ===
    try:
        cb = "jQuery_news"
        ip = json.dumps({"uid":"","keyword":code,"type":["cmsArticleWebOld"],"client":"web",
            "clientType":"web","clientVersion":"curr",
            "param":{"cmsArticleWebOld":{"searchScope":"default","sort":"default",
            "pageIndex":1,"pageSize":10,"preTag":"","postTag":""}}}, separators=(',',':'))
        r2 = sess.get("https://search-api-web.eastmoney.com/search/jsonp",
            params={"cb": cb, "param": ip},
            headers={"User-Agent": UA, "Referer": "https://so.eastmoney.com/"}, timeout=15)
        text = r2.text
        if '(' in text and text.endswith(')'):
            data = json.loads(text[text.index('(')+1:text.rindex(')')])
            for a in (data.get("result",{}).get("cmsArticleWebOld",{}).get("list",[]) or []):
                try:
                    cur.execute("""
                        INSERT IGNORE INTO info_stock_news
                        (stock_code, stock_name, title, publish_time, content_summary, source, url)
                        VALUES(%s,%s,%s,%s,%s,%s,%s)
                    """, (code, name, re.sub(r'<[^>]+>','',a.get("title",""))[:500],
                          a.get("date",""), re.sub(r'<[^>]+>','',a.get("content",""))[:500],
                          a.get("mediaName","")[:100], a.get("url","")[:1000]))
                    total_news += cur.rowcount
                except: pass
    except: pass

    if (i+1) % 100 == 0:
        log.info(f"  {i+1}/{len(hot_stocks)}: 研报新增{total_reports} 新闻新增{total_news}")
    time.sleep(0.15)

cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_research_report")
rc, rs = cur.fetchone()
cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_stock_news")
nc, ns = cur.fetchone()
log.info(f"研报: {rc}条/{rs}只 | 新闻: {nc}条/{ns}只")
conn.close()
