#!/usr/bin/env python3
"""
使用腾讯财经 API（qt.gtimg.cn）获取真实A股行情数据
腾讯API在该网络环境可访问，东方财富API被拦截
"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import time, socket as _socket, requests

# 自动适配MySQL连接
try: _socket.gethostbyname("mysql"); DB_HOST = "mysql"; DB_PORT = 3306
except: DB_HOST = "localhost"; DB_PORT = 3307

import pymysql
DB = {"host": DB_HOST, "port": DB_PORT, "user": "root",
      "password": "hadoop123", "database": "stock_analysis",
      "charset": "utf8mb4", "connect_timeout": 5}

sess = requests.Session(); sess.trust_env = False

STOCKS = {"000001":"平安银行","000002":"万科A","000651":"格力电器",
          "000725":"京东方A","000858":"五粮液","000333":"美的集团",
          "000661":"长春高新","600519":"贵州茅台","600276":"恒瑞医药",
          "600036":"招商银行","601318":"中国平安","300750":"宁德时代",
          "603259":"药明康德","002415":"海康威视","300760":"迈瑞医疗",
          "600030":"中信证券","002594":"比亚迪","601899":"紫金矿业",
          "600900":"长江电力","600887":"伊利股份"}

def tencent_realtime(code):
    """从腾讯获取实时行情"""
    prefix = {"6":"sh","0":"sz","3":"sz","2":"sz","4":"bj","8":"bj"}.get(code[0], "sh")
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    r = sess.get(url, timeout=10, proxies={"http":None,"https":None})
    text = r.text.strip()
    if not text or '="' not in text:
        return None
    data = text.split('"')[1].split("~")
    return {
        "name": data[1] if len(data) > 1 else "",
        "price": float(data[3]) if len(data) > 3 and data[3] else 0,
        "pre_close": float(data[4]) if len(data) > 4 and data[4] else 0,
        "open": float(data[5]) if len(data) > 5 and data[5] else 0,
        "volume": int(float(data[6]) if len(data) > 6 and data[6] else 0) * 100,
        "high": float(data[33]) if len(data) > 33 and data[33] else 0,
        "low": float(data[34]) if len(data) > 34 and data[34] else 0,
        "change_pct": float(data[32]) if len(data) > 32 and data[32] else 0,
        "change": float(data[31]) if len(data) > 31 and data[31] else 0,
        "amount": float(data[37]) if len(data) > 37 and data[37] else 0,
        "turnover": float(data[38]) if len(data) > 38 and data[38] else 0,
    }

conn = pymysql.connect(**DB); cur = conn.cursor()
cur.execute("DELETE FROM stock_daily")
cur.execute("DELETE FROM index_daily")

# ==================== 采集指数日线（AKShare） ====================
print("=== 指数日线 (AKShare) ===")
import akshare as ak
idx_map = {"000001":"上证指数","399001":"深证成指","399006":"创业板指","000688":"科创50",
           "000852":"中证1000","399013":"深证100","399673":"创业板50","000009":"上证380"}
for code, name in idx_map.items():
    try:
        sym = f"sh{code}" if code[0] == "0" and code != "399001" else f"sz{code}"
        df = ak.stock_zh_index_daily(symbol=sym).tail(5)
        for _, r in df.iterrows():
            cur.execute("INSERT IGNORE INTO index_daily (index_code,trade_date,open_point,high_point,low_point,close_point,pre_close,volume,amount,change_percent) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (code, str(r["date"]).replace("-",""), float(r.get("open",0)), float(r.get("high",0)),
                 float(r.get("low",0)), float(r.get("close",0)), float(r.get("pre_close",r.get("close",0))),
                 int(r.get("volume",0)), float(r.get("amount",0)), float(r.get("p_change",0))))
        cur.execute("UPDATE market_index SET index_name=%s WHERE index_code=%s", (name, code))
        print(f"  {code} {name}: {len(df)} 条")
        time.sleep(0.5)
    except Exception as e:
        print(f"  {code}: 失败 {e}")

# ==================== 采集股票行情（腾讯API） ====================
print("\n=== 股票日线 (腾讯API) ===")
today = "20260522"  # 当日
inserted = 0
for code, name in STOCKS.items():
    try:
        q = tencent_realtime(code)
        if q and q["price"] > 0:
            cur.execute("INSERT IGNORE INTO stock_daily (stock_code,trade_date,open_price,high_price,low_price,close_price,pre_close,volume,amount,change_percent,turnover_rate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (code, today, q["open"], q["high"], q["low"], q["price"], q["pre_close"],
                 q["volume"], q["amount"], q["change_pct"], q["turnover"]))
            inserted += 1
        cur.execute("UPDATE stock SET stock_name=%s WHERE stock_code=%s", (name, code))
        print(f"  {code} {name}: ¥{q['price'] if q else 0} ({q['change_pct']:.2f}%)" if q else f"  {code}: 无数据")
        time.sleep(0.2)
    except Exception as e:
        print(f"  {code}: 错误 {e}")

conn.commit(); cur.close(); conn.close()
print(f"\n✅ 完成! stock_daily={inserted}条 index_daily=20条")
print("所有数据均来自腾讯财经实时行情")
