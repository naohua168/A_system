#!/usr/bin/env python3
"""调试: 测试 AKShare 是否可连接"""
import os; os.environ["no_proxy"] = "*"
import akshare as ak
import pymysql
import requests

# 测试1: 直接HTTP请求
try:
    s = requests.Session()
    s.trust_env = False
    r = s.get("https://push2his.eastmoney.com/api/qt/stock/kline/get?fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=0&secid=0.000001&beg=20260515&end=20260521", timeout=10, proxies={"http": None, "https": None})
    print(f"HTTP test: {r.status_code}, len={len(r.text)}")
except Exception as e:
    print(f"HTTP test FAILED: {e}")

# 测试2: AKShare
try:
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20260515", end_date="20260521", adjust="")
    print(f"AKShare: {len(df)} rows")
    if not df.empty:
        print(df.columns.tolist())
        print(df.tail(1).to_string())
except Exception as e:
    print(f"AKShare FAILED: {e}")

# 测试3: MySQL
try:
    c = pymysql.connect(host="localhost", port=3307, user="root", password="hadoop123", database="stock_analysis", charset="utf8mb4").cursor()
    c.execute("SELECT 1")
    print(f"MySQL: OK, {c.fetchone()}")
    c.close()
except Exception as e:
    print(f"MySQL FAILED: {e}")
