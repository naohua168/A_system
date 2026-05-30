import pymysql, random, sys
from datetime import datetime, timedelta

conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()
random.seed(42)
bd = datetime(2026, 5, 25)

def desc(t):
    c.execute(f"DESCRIBE {t}")
    cols = [r[0] for r in c.fetchall()]
    print(f"{t}: {cols}")
    return cols

desc('market_index')
desc('index_daily')
desc('stock')
desc('stock_daily')

# Insert market_index
for code, name, mkt in [('000001.SH','上证指数','SH'),('399001.SZ','深证成指','SZ'),('399006.SZ','创业板指','SZ'),('000688.SH','科创50','SH'),('000300.SH','沪深300','SH')]:
    c.execute("INSERT IGNORE INTO market_index (index_code, index_name, market) VALUES (%s,%s,%s)", (code,name,mkt))

# Insert index_daily (close_point, pre_close, change_percent)
for i in range(5):
    d = (bd+timedelta(days=i)).strftime('%Y-%m-%d')
    for code in ['000001.SH','399001.SZ','399006.SZ','000688.SH','000300.SH']:
        cp = round(random.uniform(3000,3500) if 'SH' in code else random.uniform(10000,12000), 2)
        pc = round(cp*(1+random.uniform(-0.03,0.03)), 2)
        chg = round((cp-pc)/pc*100, 4)
        c.execute("INSERT IGNORE INTO index_daily (index_code,trade_date,close_point,pre_close,change_percent,volume,amount) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                  (code,d,cp,pc,chg,int(random.uniform(1e8,5e9)),round(random.uniform(1e10,5e11),2)))

# Insert stocks
stocks = [
    ('600519','贵州茅台','SH','白酒'),('000858','五粮液','SZ','白酒'),('600036','招商银行','SH','银行'),
    ('601318','中国平安','SH','保险'),('300750','宁德时代','SZ','新能源'),('000333','美的集团','SZ','家电'),
    ('600276','恒瑞医药','SH','医药'),('000002','万科A','SZ','房地产'),('601012','隆基绿能','SH','光伏'),
    ('002415','海康威视','SZ','安防'),('600887','伊利股份','SH','乳制品'),('000568','泸州老窖','SZ','白酒'),
    ('600900','长江电力','SH','电力'),('601899','紫金矿业','SH','有色金属'),('000001','平安银行','SZ','银行'),
    ('600030','中信证券','SH','证券'),('601166','兴业银行','SH','银行'),('000651','格力电器','SZ','家电'),
    ('600585','海螺水泥','SH','建材'),('002475','立讯精密','SZ','消费电子'),('601288','农业银行','SH','银行'),
    ('000725','京东方A','SZ','面板'),('002230','科大讯飞','SZ','人工智能'),('600309','万华化学','SH','化工'),
    ('002352','顺丰控股','SZ','物流'),('600690','海尔智家','SH','家电'),('601398','工商银行','SH','银行'),
    ('600031','三一重工','SH','机械'),('002594','比亚迪','SZ','新能源汽车'),('600570','恒生电子','SH','金融科技'),
    ('000661','长春高新','SZ','医药'),('600809','山西汾酒','SH','白酒'),('601668','中国建筑','SH','建筑'),
    ('000776','广发证券','SZ','证券'),('600588','用友网络','SH','软件'),('000895','双汇发展','SZ','食品'),
]
seen = set()
for code, name, mkt, ind in stocks:
    if code in seen: continue
    seen.add(code)
    c.execute("INSERT IGNORE INTO stock (stock_code,stock_name,market,industry,listing_date,pe,pb,total_market_cap,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
              (code,name,mkt,ind,'2020-01-01',round(random.uniform(10,80),2),round(random.uniform(1,15),2),round(random.uniform(1e10,2e12),2),1))

# Insert stock_daily (close_price, pre_close, change_percent)
for code in seen:
    for i in range(5):
        d = (bd+timedelta(days=i)).strftime('%Y-%m-%d')
        bp = round(random.uniform(10,200),2)
        close = round(bp+random.uniform(-5,5),2)
        chg = round((close-bp)/bp*100,4)
        vol = int(random.uniform(1e6,1e8))
        c.execute("INSERT IGNORE INTO stock_daily (stock_code,trade_date,open_price,high_price,low_price,close_price,pre_close,change_percent,volume,amount) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                  (code,d,round(bp-1,2),round(close+2,2),round(bp-2,2),close,bp,chg,vol,round(vol*close,2)))

conn.commit()
conn.close()
print("ALL DONE! Stocks:", len(seen))
