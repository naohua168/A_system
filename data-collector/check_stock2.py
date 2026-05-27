import pymysql
c = pymysql.connect(host='mysql',port=3306,user='root',password='hadoop123',database='stock_analysis')
cur = c.cursor()
# Check stock_daily data
cur.execute("SELECT COUNT(*), MAX(trade_date) FROM stock_daily WHERE stock_code='301591'")
r = cur.fetchone()
print(f'stock_daily 301591: {r[0]}条, 最新日期: {r[1]}')
if r[0] == 0:
    cur.execute("SELECT COUNT(*) FROM stock_daily")
    print(f'总 stock_daily 条数: {cur.fetchone()[0]}')
    cur.execute("SELECT stock_code, COUNT(*) FROM stock_daily GROUP BY stock_code ORDER BY COUNT(*) DESC LIMIT 5")
    print('数据最多的股票:')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]}条')
cur.close()
c.close()
