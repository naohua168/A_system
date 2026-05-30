"""MySQL 清理：删除市场数据表，只保留 user/watchlist"""
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()
c.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME NOT IN ('user','watchlist')", ('stock_analysis',))
tables = [r[0] for r in c.fetchall()]
for t in tables:
    c.execute(f"DROP TABLE IF EXISTS {t}")
    print(f"  已删除: {t}")
conn.commit()
conn.close()
print(f"\n共删除 {len(tables)} 张市场数据表。MySQL 仅剩 user + watchlist")
