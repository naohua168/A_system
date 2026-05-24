#!/usr/bin/env python3
"""仅导出MySQL数据到CSV"""
import pymysql, csv, os
conn = pymysql.connect(host='mysql',port=3306,user='root',password='hadoop123',database='stock_analysis',charset='utf8mb4')
c=conn.cursor()

c.execute("SELECT stock_code,stock_name,IFNULL(industry,'未知'),IFNULL(market,'A'),IFNULL(pe,0) FROM stock")
with open('/tmp/stock_basic.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    for r in c.fetchall(): w.writerow(r)
print(f'stock_basic.csv: {os.path.getsize("/tmp/stock_basic.csv")} bytes')

c.execute("SELECT stock_code,trade_date,open_price,close_price,high_price,low_price,pre_close,volume,amount,change_percent,turnover_rate,trade_date FROM stock_daily")
with open('/tmp/stock_daily.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    for r in c.fetchall(): w.writerow(r)
print(f'stock_daily.csv: {os.path.getsize("/tmp/stock_daily.csv")} bytes')

c.close();conn.close()
print('Export done')
