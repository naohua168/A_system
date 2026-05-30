"""清理 fund 表脏数据"""
import pymysql
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()
# 保留有效基金代码（含 .OF/OF）
c.execute("DELETE FROM fund WHERE fund_code NOT LIKE '%.OF'")
c.execute("DELETE FROM fund_nav WHERE fund_code NOT LIKE '%.OF'")
c.execute("DELETE FROM fund_holding WHERE fund_code NOT LIKE '%.OF'")
conn.commit()
c.execute("SELECT COUNT(*) FROM fund")
print("Fund remaining:", c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM fund_nav")
print("Fund nav remaining:", c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM fund_holding")
print("Fund holdings remaining:", c.fetchone()[0])
conn.close()
