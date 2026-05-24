#!/usr/bin/env python3
"""检查数据库数据"""
import pymysql
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis', charset='utf8mb4')
c = conn.cursor()

print('=== index_daily ===')
c.execute('SELECT index_code, trade_date, close_point, change_percent FROM index_daily ORDER BY index_code, trade_date')
for r in c.fetchall():
    print(f'  {r[0]} {r[1]}: close={r[2]}, change={r[3]}%')

print('\n=== stock_daily 行数 ===')
c.execute('SELECT COUNT(*), MAX(trade_date) FROM stock_daily')
r = c.fetchone()
print(f'  行数={r[0]}, 最新交易日={r[1]}')

print('\n=== stock_daily 样本 ===')
c.execute('''SELECT sd.stock_code, s.stock_name, sd.close_price, sd.change_percent, sd.turnover_rate
  FROM stock_daily sd JOIN stock s ON sd.stock_code=s.stock_code LIMIT 10''')
for r in c.fetchall():
    print(f'  {r[0]} {r[1]}: price={r[2]}, change={r[3]}%, turnover={r[4]}')

# 检查后端查询能否找到数据
print('\n=== 最新交易日 JOIN 测试 ===')
c.execute('SELECT COUNT(*) FROM stock_daily WHERE trade_date=(SELECT MAX(trade_date) FROM stock_daily)')
r = c.fetchone()
print(f'  最新交易日的数据行数: {r[0]}')

c.execute('SELECT stock_code, close_price, change_percent FROM stock_daily WHERE trade_date=(SELECT MAX(trade_date) FROM stock_daily) LIMIT 5')
for r in c.fetchall():
    print(f'  {r[0]}: price={r[1]}, change={r[2]}%')
c.close(); conn.close()
