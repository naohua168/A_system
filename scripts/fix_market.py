import pymysql
conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()
cur.execute("UPDATE stock SET market='SH' WHERE stock_code REGEXP '^[69]'")
print(f"SH: {cur.rowcount}")
cur.execute("UPDATE stock SET market='SZ' WHERE stock_code REGEXP '^[03]'")
print(f"SZ: {cur.rowcount}")
cur.execute("UPDATE stock SET market='BJ' WHERE stock_code REGEXP '^[84]'")
print(f"BJ: {cur.rowcount}")
cur.execute("SELECT COUNT(*) FROM stock WHERE market IS NULL")
print(f"NULL: {cur.fetchone()[0]}")
conn.close()
