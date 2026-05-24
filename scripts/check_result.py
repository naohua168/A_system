#!/usr/bin/env python3
"""检查数据库采集结果并修复股票名称"""
import pymysql
c = pymysql.connect(host='localhost', port=3307, user='root', password='hadoop123', database='stock_analysis', charset='utf8mb4').cursor()

# 检查 stock_daily 数据量
c.execute("SELECT COUNT(*), MAX(trade_date), MIN(trade_date) FROM stock_daily")
r = c.fetchone()
print(f"stock_daily: {r[0]} 行, 最新={r[1]}, 最旧={r[2]}")

# 检查哪些 stock_code 有数据
c.execute("SELECT stock_code, COUNT(*) FROM stock_daily GROUP BY stock_code ORDER BY COUNT(*) DESC LIMIT 5")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} rows")

# 检查最新日期的样本数据
c.execute("SELECT sd.stock_code, s.stock_name, sd.close_price, sd.change_percent, sd.turnover_rate FROM stock_daily sd JOIN stock s ON sd.stock_code=s.stock_code WHERE sd.trade_date=(SELECT MAX(trade_date) FROM stock_daily) LIMIT 5")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]}: price={r[2]}, change={r[3]}%, turnover={r[4]}")

c.close()
