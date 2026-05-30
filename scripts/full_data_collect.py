"""全量数据生成 - 基于真实 5542 只股票"""
import pymysql, random
from datetime import datetime, timedelta

conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()
random.seed(42)
print('开始生成全量数据...')

# 1. 清除旧数据（所有非核心表）
for t in ['stock_daily','signal_northbound','signal_hot_reason','signal_daily_industry',
          'signal_dragon_tiger_detail','signal_fund_flow','signal_lockup_detail',
          'signal_concept_block','info_cls_news','info_global_news','fund','fund_nav',
          'fund_holding','index_daily','market_index']:
    c.execute(f'TRUNCATE TABLE {t}')
    print(f'  清空 {t}')

# 2. 行业分配
industries = ['银行','白酒','医药','新能源','半导体','家电','汽车','证券','房地产','煤炭',
              '电力','化工','有色金属','建筑','食品饮料','机械设备','通信','计算机','军工','农业',
              '保险','钢铁','纺织服装','交通运输','传媒','电子','石油石化','环保','商贸零售','建材']
c.execute("SELECT stock_code FROM stock")
all_codes = [r[0] for r in c.fetchall()]
print(f'股票总数: {len(all_codes)}')

for code in all_codes:
    c.execute("UPDATE stock SET industry=%s WHERE stock_code=%s", (random.choice(industries), code))
conn.commit()
print('[1] 行业分配完成')

# 3. 日线数据（最近 5 个交易日, 模拟涨跌）
base = datetime(2026, 5, 25)
batch_daily = []
for code in all_codes:
    bp = round(random.uniform(5, 200), 2)
    for i in range(5):
        d = (base + timedelta(days=i)).strftime('%Y-%m-%d')
        close = round(bp + random.uniform(-5, 5), 2)
        chg = round((close-bp)/bp*100, 4)
        vol = int(random.uniform(1e5, 5e7))
        batch_daily.append((code, d, round(bp-1,2), round(close+2,2), round(bp-2,2), close, bp, chg, vol, round(vol*close,2)))
for i in range(0, len(batch_daily), 500):
    c.executemany("INSERT INTO stock_daily (stock_code,trade_date,open_price,high_price,low_price,close_price,pre_close,change_percent,volume,amount) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", batch_daily[i:i+500])
conn.commit()
print(f'[2] 日线: {len(batch_daily)} 条')

# 4. 指数数据
indices = [('000001.SH','上证指数','SH'),('399001.SZ','深证成指','SZ'),
           ('399006.SZ','创业板指','SZ'),('000688.SH','科创50','SH'),
           ('000300.SH','沪深300','SH')]
for code, name, mkt in indices:
    c.execute("INSERT INTO market_index (index_code,index_name,market) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE index_name=VALUES(index_name)", (code, name, mkt))
for i in range(5):
    d = (base+timedelta(days=i)).strftime('%Y-%m-%d')
    for code in [x[0] for x in indices]:
        cp = round(random.uniform(3000,3500) if 'SH' in code else random.uniform(10000,12000),2)
        pc = round(cp*(1+random.uniform(-0.03,0.03)),2)
        c.execute("INSERT INTO index_daily (index_code,trade_date,close_point,pre_close,change_percent,volume,amount) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                  (code,d,cp,pc,round((cp-pc)/pc*100,4),int(random.uniform(1e8,5e9)),round(random.uniform(1e10,5e11),2)))
conn.commit()
print('[3] 指数数据完成')

# 5. 信号层
for i in range(21):  # 21 trading days
    d = (datetime.now()-timedelta(days=i)).strftime('%Y-%m-%d')
    wd = datetime.strptime(d,'%Y-%m-%d').weekday()
    if wd >= 5: continue
    c.execute("INSERT INTO signal_northbound (trade_date, hgt_yi, sgt_yi) VALUES (%s,%s,%s)",
              (d, round(random.uniform(100,600),2), round(random.uniform(50,300),2)))
print('[4.1] 北向资金完成')

themes = ['AI算力','低空经济','半导体','新能源汽车','人形机器人','光伏出海']
reasons = ['政策利好频出','产业趋势明确','国产替代加速','需求回暖']
for code in all_codes[:500]:
    c.execute("INSERT INTO signal_hot_reason (trade_date,stock_code,stock_name,reason,change_pct) VALUES (%s,%s,%s,%s,%s)",
              ('2026-05-29', code, '', f'{random.choice(themes)}: {random.choice(reasons)}', round(random.uniform(-3,10),2)))
conn.commit()
print('[4.2] 题材热点: 500 条')

for i, ind in enumerate(industries, 1):
    c.execute("INSERT INTO signal_daily_industry (trade_date,rank_num,industry_name,change_pct,up_count,down_count) VALUES (%s,%s,%s,%s,%s,%s)",
              ('2026-05-29', i, ind, round(random.uniform(-3,5),2), random.randint(5,30), random.randint(1,10)))
conn.commit()
print('[4.3] 行业对比完成')

for code in all_codes[:100]:
    c.execute("INSERT INTO signal_dragon_tiger_detail (trade_date,stock_code,reason,close,change_pct,net_buy_wan,buy_wan,sell_wan,turnover_pct) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
              ('2026-05-29', code, '日涨幅偏离值达7%', round(random.uniform(10,80),2), round(random.uniform(7,11),2), round(random.uniform(1000,50000),2), round(random.uniform(2000,80000),2), round(random.uniform(1000,40000),2), round(random.uniform(15,50),2)))
conn.commit()
print('[4.4] 龙虎榜: 100 条')

for code in all_codes[:500]:
    c.execute("INSERT INTO signal_fund_flow (stock_code,trade_date,close,change_pct,super_net_in,large_net_in,medium_net_in,little_net_in,main_in) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
              (code,'2026-05-29',round(random.uniform(10,100),2),f'{round(random.uniform(-5,5),2)}%',str(random.randint(-10000,20000)),str(random.randint(-5000,10000)),str(random.randint(-3000,5000)),str(random.randint(-2000,3000)),str(random.randint(-8000,15000))))
conn.commit()
print('[4.5] 资金流向: 500 条')

for code in all_codes[:300]:
    c.execute("INSERT INTO signal_lockup_detail (stock_code,lockup_date,lockup_type,shares,float_ratio,ratio,type_tag) VALUES (%s,%s,%s,%s,%s,%s,%s)",
              (code,'2026-06-15','定向增发机构配售股份',round(random.uniform(1e6,5e8),2),f'{round(random.uniform(1,30),1)}%',f'{round(random.uniform(0.5,15),1)}%','upcoming'))
conn.commit()
print('[4.6] 限售解禁: 300 条')

concepts = ['人工智能','芯片','新能源','5G','大数据','云计算','军工','央企改革','一带一路','碳中和']
for code in all_codes[:500]:
    for blk in random.sample(concepts, random.randint(1,2)):
        c.execute("INSERT INTO signal_concept_block (stock_code,block_type,block_name) VALUES (%s,%s,%s)", (code,'concept',blk))
conn.commit()
print('[4.7] 概念板块: ~750 条')

# 6. 资讯
cls_news = [
    ('【发改委】将出台促进AI产业发展行动方案','国家发改委表示将出台促进AI产业发展行动方案','2026-05-29 15:30'),
    ('【央行】开展2000亿元MLF操作','央行今日开展2000亿元MLF操作，利率维持不变','2026-05-29 15:00'),
    ('【A股】三大指数集体收涨沪指重回3100点','A股三大指数集体收涨，两市成交额超万亿','2026-05-29 15:02'),
    ('【北向】北向资金全天净买入68.5亿元','北向资金大幅净买入68.5亿元','2026-05-29 15:05'),
    ('【半导体】中芯国际拟投资千亿建新厂','中芯国际公告拟投资1000亿元建设先进制程芯片工厂','2026-05-29 13:00'),
    ('【新能源】4月新能源汽车销量同比增长35%','中汽协：4月新能源汽车销量95万辆同比增长35%','2026-05-29 11:30'),
    ('【房地产】5月楼市成交环比增20%','机构数据显示30城商品房成交面积环比增长20%','2026-05-29 10:00'),
    ('【美联储】多数官员支持年内降息','美联储会议纪要显示多数官员支持年内降息','2026-05-29 08:00'),
    ('【美股】三大指数小幅收涨','美股三大指数小幅收涨，纳指涨0.3%','2026-05-29 06:00'),
    ('【行业】AI算力需求爆发','AI算力板块走强','2026-05-28 22:00'),
]
for title, content, dt in cls_news:
    c.execute("INSERT INTO info_cls_news (title,content,datetime,source) VALUES (%s,%s,%s,%s)", (title,content,dt,'财联社'))

gnews = [
    ('美联储会议纪要：通胀顽固','美联储公布最新会议纪要，显示通胀仍顽固','2026-05-29 07:30'),
    ('欧盟通过对华电动汽车反补贴调查裁定','欧盟委员会通过对中国电动汽车反补贴调查初步裁定','2026-05-29 06:00'),
    ('OPEC+维持产量计划不变','OPEC+会议决定维持当前产量计划不变','2026-05-28 22:00'),
    ('日本央行维持利率不变','日本央行宣布维持政策利率不变','2026-05-28 14:00'),
    ('全球半导体销售额连续6月正增长','SIA数据显示全球半导体销售额连续6个月同比增长','2026-05-28 10:00'),
]
for title, content, dt in gnews:
    c.execute("INSERT INTO info_global_news (title,content,datetime,source) VALUES (%s,%s,%s,%s)", (title,content,dt,'东方财富'))
conn.commit()
print('[5] 资讯数据完成')

# 7. 基金
funds = [('000001.OF','华夏成长混合','混合型'),('000011.OF','华夏大盘精选混合','混合型'),
         ('110011.OF','易方达中小盘混合','混合型'),('110022.OF','易方达消费行业','股票型'),
         ('161725.OF','招商中证白酒指数','指数型'),('001714.OF','工银文体产业','股票型'),
         ('003096.OF','中欧医疗健康混合','混合型'),('005827.OF','易方达蓝筹精选','混合型'),
         ('519772.OF','交银新生活力','混合型'),('006345.OF','景顺长城核心优选','混合型')]
for code, name, ftype in funds:
    c.execute("INSERT INTO fund (fund_code,fund_name,fund_type,status) VALUES (%s,%s,%s,1)", (code,name,ftype))

for fc in [f[0] for f in funds]:
    for i in range(30):
        d = (datetime.now()-timedelta(days=i)).strftime('%Y-%m-%d')
        if datetime.strptime(d,'%Y-%m-%d').weekday() >= 5: continue
        nav = round(random.uniform(0.8,3.5),4)
        c.execute("INSERT INTO fund_nav (fund_code,nav_date,nav,accumulated_nav) VALUES (%s,%s,%s,%s)",
                  (fc,d,nav,round(nav*random.uniform(1.0,1.2),4)))

c.execute("SELECT stock_code FROM stock LIMIT 30")
top_stocks = [r[0] for r in c.fetchall()]
for fc in [f[0] for f in funds]:
    for rank, sc in enumerate(random.sample(top_stocks, min(10,len(top_stocks))), 1):
        c.execute("INSERT INTO fund_holding (fund_code,report_date,stock_code,ratio,rank_num) VALUES (%s,%s,%s,%s,%s)",
                  (fc,'2026-03-31',sc,round(random.uniform(0.5,15),2),rank))
conn.commit()
print('[6] 基金数据完成')

conn.close()
print('\n===== 全量数据生成完成 =====')
