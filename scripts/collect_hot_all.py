#!/usr/bin/env python3
"""
采集全量热点题材历史数据: 2025-01-01 ~ 2026-03-31
跳过已存在的日期
"""
import os, time, logging, requests, pymysql
from datetime import datetime, timedelta

os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# 获取已有日期
cur.execute("SELECT DISTINCT trade_date FROM signal_hot_reason")
existing = {r[0] for r in cur.fetchall()}
log.info(f"已有 {len(existing)} 个交易日")

# 生成待采集日期: 2025-01-01 ~ 2026-03-31
start = datetime(2025, 1, 1)
end = datetime(2026, 3, 31)
dates = []
d = start
while d <= end:
    ds = d.strftime("%Y-%m-%d")
    if ds not in existing:
        dates.append(ds)
    d += timedelta(days=1)

log.info(f"待采集: {len(dates)} 天")

if not dates:
    log.info("无需采集!")
    conn.close()
    exit(0)

sess = requests.Session()
sess.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

total = errors = skipped = 0

for i, ds in enumerate(dates):
    try:
        url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{ds}/orderby/date/orderway/desc/charset/GBK/"
        r = sess.get(url, headers={"User-Agent": UA}, timeout=10)
        data = r.json()
        
        if data.get("errocode", 0) != 0:
            skipped += 1
            continue
        
        rows = data.get("data") or []
        if not rows:
            skipped += 1
            continue
        
        # 跳过非交易日（通常返回固定模板数据）
        first_name = rows[0].get("name", "")
        if len(rows) == 64 and first_name == "ST得润":
            skipped += 1
            continue
        
        inserted = 0
        for row in rows:
            try:
                code = row.get("code", "") or ""
                name = row.get("name", "") or ""
                reason = row.get("reason", "") or ""
                cp = float(row.get("zhangfu", 0) or 0)
                tp = float(row.get("huanshou", 0) or 0)
                
                cur.execute("""
                    INSERT IGNORE INTO signal_hot_reason 
                    (trade_date, stock_code, stock_name, reason, change_pct, turnover_pct)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (ds, code, name, reason, cp, tp))
                inserted += cur.rowcount
                total += 1
            except:
                pass
        
        if inserted > 0:
            log.info(f"  {ds}: {inserted} 条")
        
    except Exception as e:
        errors += 1
        if errors <= 5:
            log.warning(f"  {ds}: {e}")
    
    if (i + 1) % 100 == 0:
        log.info(f"  进度: {i+1}/{len(dates)}, 新增={total}, 跳过={skipped}, 错误={errors}")

log.info(f"完成: 新增={total}, 跳过={skipped}, 错误={errors}")

# 统计
cur.execute("SELECT COUNT(*), COUNT(DISTINCT trade_date), MIN(trade_date), MAX(trade_date) FROM signal_hot_reason")
r = cur.fetchone()
log.info(f"最终: {r[0]}条, {r[1]}天, 范围: {r[2]} ~ {r[3]}")

conn.close()
