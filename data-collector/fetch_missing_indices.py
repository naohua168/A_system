#!/usr/bin/env python3
"""补采新指数的日K线数据"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import time, socket as _socket

try: _socket.gethostbyname("mysql"); DB_HOST = "mysql"; DB_PORT = 3306
except: DB_HOST = "localhost"; DB_PORT = 3307

import pymysql, akshare as ak

DB = {"host": DB_HOST, "port": DB_PORT, "user": "root",
      "password": "hadoop123", "database": "stock_analysis",
      "charset": "utf8mb4", "connect_timeout": 5}

NEW_INDICES = [
    ("000852", "sh000852", "中证1000"),
    ("399013", "sz399013", "深证100"),
    ("399673", "sz399673", "创业板50"),
    ("000009", "sh000009", "上证380"),
]

conn = pymysql.connect(**DB); cur = conn.cursor()
total = 0

for code, sym, name in NEW_INDICES:
    try:
         # AKShare 采集
        df = ak.stock_zh_index_daily(symbol=sym)
        cnt = 0
        for _, r in df.iterrows():
            cur.execute("""INSERT IGNORE INTO index_daily
                (index_code,trade_date,open_point,high_point,low_point,close_point,pre_close,volume,amount,change_percent)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (code, str(r["date"]).replace("-",""), float(r.get("open",0)),
                 float(r.get("high",0)), float(r.get("low",0)),
                 float(r.get("close",0)), float(r.get("pre_close",r.get("close",0))),
                 int(r.get("volume",0)), float(r.get("amount",0)),
                 float(r.get("p_change",0))))
            cnt += cur.rowcount
        conn.commit()
        print(f"  ✅ {code} {name}: {cnt} 条")
        total += cnt
        time.sleep(0.5)
    except Exception as e:
        print(f"  ❌ {code} {name}: {e}")

cur.close(); conn.close()
print(f"\n完成！共写入 {total} 条指数日K数据")
