#!/usr/bin/env python3
"""容器内akshare采集stock_news，分批处理"""
import subprocess, json, pymysql, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# 获取top300高市值+龙虎榜股票
cur.execute("""
    SELECT stock_code FROM (
        SELECT stock_code FROM stock WHERE total_market_cap > 0 ORDER BY total_market_cap DESC LIMIT 200
    ) t1
    UNION 
    SELECT DISTINCT stock_code FROM signal_dragon_tiger_detail
""")
codes = [r[0] for r in cur.fetchall()[:300]]
log.info(f"目标: {len(codes)} 只股票")

# 复制脚本
subprocess.run(["docker","cp","scripts/collect_news_container.py","data-collector:/tmp/collect_news.py"], check=True)

cur.execute("SELECT COUNT(*) FROM info_stock_news")
before = cur.fetchone()[0]
total = 0
BATCH = 100

for i in range(0, len(codes), BATCH):
    batch = codes[i:i+BATCH]
    codes_str = ",".join(batch)
    
    try:
        r = subprocess.run(f'docker exec data-collector python3 /tmp/collect_news.py {codes_str}',
                          shell=True, capture_output=True, text=True, timeout=120)
        
        # 解析JSON (最后一行)
        stdout_lines = r.stdout.strip().split("\n")
        for line in reversed(stdout_lines):
            if line.strip().startswith("{"):
                data = json.loads(line)
                break
        else:
            log.error(f"批次{i//BATCH+1} JSON失败"); continue
        
        sn = data.get("stock_news", [])
        inserted = 0
        for item in sn:
            try:
                cur.execute("""
                    INSERT IGNORE INTO info_stock_news(stock_code, title, content_summary, publish_time, source, url)
                    VALUES(%s,%s,%s,%s,%s,%s)
                """, (item.get("code",""), item.get("title","")[:500],
                      item.get("content","")[:2000], item.get("time",""),
                      item.get("source","")[:100], item.get("url","")[:1000]))
                inserted += cur.rowcount
            except: pass
        total += inserted
        log.info(f"  批次{i//BATCH+1}: {inserted}条, 累计{total}")
    except subprocess.TimeoutExpired:
        log.error(f"  批次{i//BATCH+1}超时")
    except Exception as e:
        log.error(f"  批次{i//BATCH+1}: {e}")

cur.execute("SELECT COUNT(*), COUNT(DISTINCT stock_code) FROM info_stock_news")
c, s = cur.fetchone()
log.info(f"完成: stock_news={c}条/{s}只 (新增{c-before})")
conn.close()
