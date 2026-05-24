#!/usr/bin/env python3
import pymysql, json
conn = pymysql.connect(host='localhost', port=3307, user='root', password='hadoop123', database='stock_analysis', charset='utf8mb4')
c = conn.cursor()

# 检查股票名称 HEX
c.execute("SELECT stock_code, HEX(stock_name), stock_name FROM stock ORDER BY stock_code LIMIT 20")
print("=== stock 名称检查 ===")
for r in c.fetchall():
    print(f"  {r[0]}: HEX={r[1]}, name={r[2]}")

# 检查 stock_daily 最新数据
c.execute("""SELECT s.stock_code, s.stock_name, d.close_price, d.change_percent, d.turnover_rate 
  FROM stock_daily d JOIN stock s ON d.stock_code=s.stock_code 
  WHERE d.trade_date=(SELECT MAX(trade_date) FROM stock_daily) 
  LIMIT 10""")
print("\n=== 最新行情数据 ===")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]}: price={r[2]}, change={r[3]}%, turnover={r[4]}")

c.close()
conn.close()
