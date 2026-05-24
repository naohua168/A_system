#!/usr/bin/env python3
"""修复指数涨跌幅 + 尝试通达信批量采集更多股票"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import time, socket as _socket, requests

try: _socket.gethostbyname("mysql"); DB_HOST = "mysql"; DB_PORT = 3306
except: DB_HOST = "localhost"; DB_PORT = 3307

import pymysql
DB = {"host": DB_HOST, "port": DB_PORT, "user": "root", "password": "hadoop123",
      "database": "stock_analysis", "charset": "utf8mb4", "connect_timeout": 5}

sess = requests.Session(); sess.trust_env = False
conn = pymysql.connect(**DB); cur = conn.cursor()

# ============ 1. 修复指数涨跌幅 ============
print("=== 修复 index_daily change_percent ===")
cur.execute("UPDATE index_daily SET change_percent = ROUND((close_point - pre_close) / pre_close * 100, 2) WHERE pre_close > 0")
print(f"  修复 {cur.rowcount} 行")

cur.execute("SELECT index_code, trade_date, pre_close, close_point, change_percent FROM index_daily WHERE trade_date='2026-05-22'")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}: pre={r[2]}, close={r[3]}, change={r[4]}%")

# ============ 2. 采集指数实时行情（修正pre_close） ============
print("\n=== 从腾讯财经更新指数行情 ===")
idx_codes = [
    ("000001", "sh000001", "上证指数"),
    ("399001", "sz399001", "深证成指"),
    ("399006", "sz399006", "创业板指"),
    ("000688", "sh000688", "科创50"),
]
for code, sym, name in idx_codes:
    try:
        url = f"http://qt.gtimg.cn/q={sym}"
        r = sess.get(url, timeout=10, proxies={"http":None,"https":None})
        data = r.text.strip().split('"')[1].split("~")
        # 腾讯指数字段: name, code, price, pre_close
        price = float(data[3]) if len(data)>3 and data[3] else 0
        pre_close = float(data[4]) if len(data)>4 and data[4] else 0
        change = float(data[31]) if len(data)>31 and data[31] else 0
        pct = float(data[32]) if len(data)>32 and data[32] else 0
        cur.execute("UPDATE index_daily SET pre_close=%s, close_point=%s, change_percent=%s WHERE index_code=%s AND trade_date='2026-05-22'",
            (pre_close, price, pct, code))
        print(f"  {code} {name}: close={price}, pre={pre_close}, change={pct}%")
        time.sleep(0.2)
    except Exception as e:
        print(f"  {code}: 错误 {e}")

# ============ 3. 尝试通达信批量采集 ============
print("\n=== 尝试通达信 mootdx 批量采集 ===")
try:
    from mootdx.quotes import Quotes
    client = Quotes.factory(market="std")  # 标准行情
    # 获取所有A股实时行情
    codes = list(STOCKS.keys()) if 'STOCKS' in dir() else ["000001","000002","000651","000725"]
    resp = client.quotes(symbol=codes)
    if resp is not None and len(resp) > 0:
        print(f"  通达信: 获取 {len(resp)} 只股票")
        import pandas as pd
        # 处理...
    else:
        print("  通达信: 无返回数据")
except ImportError:
    print("  通达信: mootdx 未安装")
except Exception as e:
    print(f"  通达信: {e}")

conn.commit(); cur.close(); conn.close()
print("\n✅ 完成")
