#!/usr/bin/env python3
import pymysql
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis', charset='utf8mb4')
c = conn.cursor()

print('=== signal 表数据量 ===')
for tbl in ['signal_hot_reason','signal_dragon_tiger','signal_northbound','signal_lockup_detail','signal_fund_flow']:
    try:
        c.execute(f'SELECT COUNT(*) FROM {tbl}')
        print(f'  {tbl}: {c.fetchone()[0]} 行')
    except Exception as e:
        print(f'  {tbl}: {e}')

c.execute("SHOW TABLES LIKE '%industry%'")
for r in c.fetchall(): print(f'  industry表: {r[0]}')

c.execute("SHOW TABLES LIKE '%sector%'")
for r in c.fetchall(): print(f'  sector表: {r[0]}')

c.execute("SHOW TABLES LIKE '%concept%'")
for r in c.fetchall(): print(f'  concept表: {r[0]}')

c.execute("SHOW TABLES LIKE '%block%'")
for r in c.fetchall(): print(f'  block表: {r[0]}')

# stock表行业分布
c.execute("SELECT industry, COUNT(*) FROM stock WHERE industry IS NOT NULL AND industry != '' GROUP BY industry ORDER BY COUNT(*) DESC LIMIT 15")
print(f'\n=== stock表行业分布 (TOP 15) ===')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}只')

c.close(); conn.close()
