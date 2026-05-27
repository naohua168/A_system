#!/usr/bin/env python3
"""
快速采集: cls_news + global_news (容器内akshare → 本机MySQL)
"""
import subprocess, json, pymysql, logging, os

os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 1. 复制脚本到容器
subprocess.run(["docker","cp","scripts/collect_news_container.py","data-collector:/tmp/collect_news.py"], check=True)

# 2. 在容器内运行 (只采cls+global, 不传股票代码)
log.info("容器内采集 cls_news + global_news ...")
r = subprocess.run("docker exec data-collector python3 /tmp/collect_news.py ''",
                   shell=True, capture_output=True, text=True, timeout=60)

# 3. 解析JSON
stdout = r.stdout.strip()
for line in reversed(stdout.split("\n")):
    if line.startswith("{"):
        data = json.loads(line)
        break
else:
    log.error(f"JSON解析失败, stdout: {stdout[:200]}")
    exit(1)

log.info(f"cls: {len(data.get('cls_news',[]))}条, global: {len(data.get('global_news',[]))}条")

# 4. 写入MySQL
conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# cls_news
for item in data.get("cls_news", []):
    try:
        cur.execute("""
            INSERT IGNORE INTO info_cls_news(title, content, publish_time)
            VALUES(%s,%s,%s)
        """, (str(item.get("标题",""))[:500], str(item.get("内容",""))[:2000],
              f"{item.get('发布日期','')} {item.get('发布时间','')}"))
    except: pass

# global_news
for item in data.get("global_news", []):
    try:
        cur.execute("""
            INSERT IGNORE INTO info_global_news(title, summary, publish_time, source, url)
            VALUES(%s,%s,%s,%s,%s)
        """, (str(item.get("标题",""))[:500], str(item.get("摘要",""))[:2000],
              str(item.get("发布时间","")), "东财", str(item.get("链接",""))[:1000]))
    except: pass

# 统计
cur.execute("SELECT COUNT(*) FROM info_cls_news")
c1 = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM info_global_news")
c2 = cur.fetchone()[0]
log.info(f"完成: cls_news={c1}条, global_news={c2}条")

conn.close()
