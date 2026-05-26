#!/usr/bin/env python3
"""
从同花顺API采集全量热点题材历史数据
"""
import os, sys, time, logging, requests, pymysql
from datetime import datetime, timedelta

os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# 查询已存在的日期
cur.execute("SELECT DISTINCT trade_date FROM signal_hot_reason")
existing_dates = {r[0] for r in cur.fetchall()}
log.info(f"已有 {len(existing_dates)} 个交易日数据")

# 生成待查询日期: 从2026-04-01到2026-05-26的所有交易日（同花顺会自动跳过非交易日）
start_date = datetime(2026, 4, 1)
end_date = datetime(2026, 5, 26)
date = start_date
dates_to_fetch = []
while date <= end_date:
    date_str = date.strftime("%Y-%m-%d")
    if date_str not in existing_dates:
        dates_to_fetch.append(date_str)
    date += timedelta(days=1)

log.info(f"待采集: {len(dates_to_fetch)} 天")

if not dates_to_fetch:
    log.info("无需采集")
    conn.close()
    sys.exit(0)

sess = requests.Session()
sess.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

total_inserted = 0
total_errors = 0

for date_str in dates_to_fetch:
    try:
        url = f"http://zx.10jqka.com.cn/event/api/getharden/date/{date_str}/orderby/date/orderway/desc/charset/GBK/"
        r = sess.get(url, headers={"User-Agent": UA}, timeout=10)
        data = r.json()
        
        if data.get("errocode", 0) != 0:
            # 可能是非交易日
            continue
        
        rows = data.get("data") or []
        inserted = 0
        for row in rows:
            try:
                code = row.get("code", "")
                name = row.get("name", "")
                reason = row.get("reason", "")
                change_pct = float(row.get("zhangfu", 0) or 0)
                turnover_pct = float(row.get("huanshou", 0) or 0)
                
                cur.execute("""
                    INSERT IGNORE INTO signal_hot_reason 
                    (trade_date, stock_code, stock_name, reason, change_pct, turnover_pct)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (date_str, code, name, reason, change_pct, turnover_pct))
                inserted += cur.rowcount
                total_inserted += 1
            except:
                pass
        
        log.info(f"  {date_str}: {inserted} 条")
        
    except Exception as e:
        total_errors += 1
        if total_errors <= 5:
            log.warning(f"  {date_str}: {e}")
    
    time.sleep(0.1)

log.info(f"完成: 新增={total_inserted}, 错误={total_errors}")

# 统计
cur.execute("SELECT COUNT(*), COUNT(DISTINCT trade_date) FROM signal_hot_reason")
total_rows, total_dates = cur.fetchone()
cur.execute("SELECT MIN(trade_date), MAX(trade_date) FROM signal_hot_reason")
date_range = cur.fetchone()
log.info(f"热点数据: {total_rows} 条, {total_dates} 个交易日 ({date_range[0]} ~ {date_range[1]})")

conn.close()
