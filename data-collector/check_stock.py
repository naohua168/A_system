import pymysql
c = pymysql.connect(host='mysql',port=3306,user='root',password='hadoop123',database='stock_analysis')
cur = c.cursor()
cur.execute('SELECT COUNT(*) FROM stock')
print(f'总股票数: {cur.fetchone()[0]}')
cur.execute("SELECT stock_code,stock_name FROM stock WHERE stock_code='301591'")
r = cur.fetchone()
print(f'301591存在: {r}' if r else '301591不存在')
if not r:
    cur.execute('SELECT stock_code,stock_name FROM stock ORDER BY stock_code LIMIT 5')
    for row in cur.fetchall():
        print(f'  {row[0]} {row[1]}')
cur.close()
c.close()
