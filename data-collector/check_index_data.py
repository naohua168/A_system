#!/usr/bin/env python3
import pymysql
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123',
                       database='stock_analysis', charset='utf8mb4')
cur = conn.cursor()
# 最新交易日各大指数行情
cur.execute("""
    SELECT i.index_code, i.index_name, d.close_point, d.change_percent, d.trade_date
    FROM market_index i
    LEFT JOIN index_daily d ON i.index_code = d.index_code
        AND d.trade_date = (SELECT MAX(trade_date) FROM index_daily)
    ORDER BY i.index_code
""")
print(f"{'代码':>8} {'名称':<10} {'收盘':>10} {'涨跌幅':>8} {'日期':<12}")
print("-"*50)
for r in cur.fetchall():
    close = f"{float(r[2]):.2f}" if r[2] else "---"
    pct = f"{float(r[3]):.2f}%" if r[3] else "---"
    date = str(r[4]) if r[4] else "---"
    print(f"{r[0]:>8} {r[1]:<10} {close:>10} {pct:>8} {date:<12}")
cur.close()
conn.close()
