#!/usr/bin/env python3
"""综合修复：修正指数pre_close+涨跌幅 + 通达信/腾讯批量采集股票"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import time, socket as _socket, requests

try: _socket.gethostbyname("mysql"); DB_HOST = "mysql"; DB_PORT = 3306
except: DB_HOST = "localhost"; DB_PORT = 3307

import pymysql
DB = {"host": DB_HOST, "port": DB_PORT, "user": "root", "password": "hadoop123",
      "database": "stock_analysis", "charset": "utf8mb4", "connect_timeout": 5}

sess = requests.Session(); sess.trust_env = False
conn = pymysql.connect(**DB); cur = conn.cursor()

# ============ 1. 修复 index_daily pre_close 和 change_percent ============
print("=== 修复指数日线 涨跌幅 ===")
# 用前一天的close作为当天的pre_close
cur.execute("""
  UPDATE index_daily t1
  JOIN index_daily t2 ON t1.index_code = t2.index_code
    AND t2.trade_date = DATE_SUB(t1.trade_date, INTERVAL 1 DAY)
  SET t1.pre_close = t2.close_point,
      t1.change_percent = ROUND((t1.close_point - t2.close_point) / t2.close_point * 100, 2)
  WHERE t2.close_point > 0
""")
print(f"  修复 {cur.rowcount} 行")

cur.execute("SELECT index_code, trade_date, close_point, pre_close, change_percent FROM index_daily WHERE trade_date='2026-05-22' ORDER BY index_code")
print("  (最新交易日)")
for r in cur.fetchall():
    print(f"    {r[0]}: close={r[2]}, pre={r[3]}, change={r[4]}%")

# ============ 2. 腾讯批量采集更多股票 ============
print("\n=== 腾讯批量采集 ===")
# 获取stock表中所有有名称的股票代码，过滤前100只
cur.execute("SELECT stock_code FROM stock WHERE stock_code REGEXP '^[0-6]' AND LENGTH(stock_code)=6 LIMIT 200")
all_codes = [r[0] for r in cur.fetchall()]
# 去掉已有数据的
cur.execute("SELECT DISTINCT stock_code FROM stock_daily")
existing = set(r[0] for r in cur.fetchall())
new_codes = [c for c in all_codes if c not in existing]

print(f"  已有数据: {len(existing)} 只, 待采集: {len(new_codes)} 只")

# 分批采集（腾讯API一次获取一只）
batch_size = 50
today = "20260522"
inserted_new = 0

for i in range(0, min(len(new_codes), batch_size)):
    code = new_codes[i]
    prefix = {"6":"sh","0":"sz","3":"sz","2":"sz"}.get(code[0], "sh")
    try:
        url = f"http://qt.gtimg.cn/q={prefix}{code}"
        r = sess.get(url, timeout=10, proxies={"http":None,"https":None})
        data = r.text.strip()
        if '="' not in data: continue
        parts = data.split('"')[1].split("~")
        if len(parts) < 39: continue
        price = float(parts[3]) if parts[3] else 0
        if price <= 0: continue
        pre_close = float(parts[4]) if parts[4] else 0
        high = float(parts[33]) if parts[33] else 0
        low = float(parts[34]) if parts[34] else 0
        vol = int(float(parts[6]) * 100) if parts[6] else 0
        amt = float(parts[37]) if parts[37] else 0
        pct = float(parts[32]) if parts[32] else 0
        turnover = float(parts[38]) if parts[38] else 0
        cur.execute("INSERT IGNORE INTO stock_daily (stock_code,trade_date,open_price,close_price,high_price,low_price,pre_close,volume,amount,change_percent,turnover_rate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (code, today, float(parts[5]) if parts[5] else 0, price, high, low, pre_close, vol, amt, pct, turnover))
        inserted_new += 1
        time.sleep(0.15)
        if i % 10 == 9:
            conn.commit()
            n = sum(1 for x in range(max(0,i-9), i+1) if x < len(new_codes))
            print(f"  进度: {i+1}/{min(len(new_codes),batch_size)}, 已插入{inserted_new}")
    except:
        continue

conn.commit()
print(f"  新增 {inserted_new} 只股票日线数据")

# ============ 3. 统计 ============
cur.execute("SELECT COUNT(*), MAX(trade_date), MIN(trade_date) FROM stock_daily")
r = cur.fetchone()
print(f"\nstock_daily 总计: {r[0]} 行, {r[1]} ~ {r[2]}")

cur.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_daily")
print(f"覆盖股票: {cur.fetchone()[0]} 只")

cur.execute("SELECT COUNT(*) FROM index_daily WHERE ABS(change_percent) > 0.01")
print(f"指数有涨跌幅数据: {cur.fetchone()[0]} 行")

cur.close(); conn.close()
print("\n✅ 综合修复完成")
