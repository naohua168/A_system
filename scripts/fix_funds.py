"""修复基金数据"""
import pymysql, random
from datetime import datetime, timedelta

conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()
random.seed(42)

funds = [('000001.OF','华夏成长混合','混合型'),('000011.OF','华夏大盘精选混合','混合型'),
         ('110011.OF','易方达中小盘混合','混合型'),('110022.OF','易方达消费行业','股票型'),
         ('161725.OF','招商中证白酒指数','指数型'),('001714.OF','工银文体产业','股票型'),
         ('003096.OF','中欧医疗健康混合','混合型'),('005827.OF','易方达蓝筹精选','混合型'),
         ('519772.OF','交银新生活力','混合型'),('006345.OF','景顺长城核心优选','混合型')]
for code, name, ftype in funds:
    c.execute('INSERT IGNORE INTO fund (fund_code,fund_name,fund_type,status) VALUES (%s,%s,%s,1)', (code,name,ftype))
conn.commit()

for fc in [f[0] for f in funds]:
    for i in range(30):
        d = (datetime.now()-timedelta(days=i)).strftime('%Y-%m-%d')
        if datetime.strptime(d,'%Y-%m-%d').weekday() >= 5: continue
        nav = round(random.uniform(0.8,3.5),4)
        c.execute('INSERT IGNORE INTO fund_nav (fund_code,nav_date,nav,accumulated_nav) VALUES (%s,%s,%s,%s)', (fc,d,nav,round(nav*random.uniform(1.0,1.2),4)))

c.execute('SELECT stock_code, stock_name FROM stock LIMIT 30')
stocks = c.fetchall()
for fc in [f[0] for f in funds]:
    sample = random.sample(stocks, min(10, len(stocks)))
    for rank, (sc, sn) in enumerate(sample, 1):
        c.execute('INSERT INTO fund_holding (fund_code,report_date,stock_code,stock_name,ratio,rank_num) VALUES (%s,%s,%s,%s,%s,%s)', (fc,'2026-03-31',sc,sn,round(random.uniform(0.5,15),2),rank))
conn.commit()

c.execute('SELECT COUNT(*) FROM fund, fund_nav, fund_holding')
print('All fund data inserted')
conn.close()
