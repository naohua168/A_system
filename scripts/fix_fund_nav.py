import pymysql, random
from datetime import datetime, timedelta
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()
random.seed(42)
c.execute('SELECT fund_code FROM fund')
fcs = [r[0] for r in c.fetchall()]
n = 0
for fc in fcs:
    for i in range(30):
        d = (datetime.now()-timedelta(days=i)).strftime('%Y-%m-%d')
        if datetime.strptime(d,'%Y-%m-%d').weekday() >= 5: continue
        nav = round(random.uniform(0.8,3.5),4)
        c.execute('INSERT IGNORE INTO fund_nav (fund_code,nav_date,nav,accumulated_nav) VALUES (%s,%s,%s,%s)', (fc,d,nav,round(nav*random.uniform(1.0,1.2),4)))
        n += 1
conn.commit()
print(f'Fund nav: {n}')
conn.close()
