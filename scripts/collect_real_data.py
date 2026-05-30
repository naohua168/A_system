"""用 akshare 采集全市场真实日K线数据"""
import pymysql, time
from datetime import datetime

conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()

# 获取所有股票代码
c.execute("SELECT stock_code FROM stock ORDER BY stock_code")
all_codes = [r[0] for r in c.fetchall()]
print(f"总计 {len(all_codes)} 只股票")

# 分批采集
import akshare as ak

total_inserted = 0
batch_size = 200  # 每批200只

for batch_start in range(0, min(len(all_codes), 2000), batch_size):
    batch = all_codes[batch_start:batch_start + batch_size]
    print(f"\n批次 {batch_start//batch_size + 1}/{(min(len(all_codes),2000)//batch_size)}: {batch[0]} ~ {batch[-1]}")
    
    for code in batch:
        try:
            # 使用 akshare 获取历史日K（后复权）
            df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date='20250101', end_date='20260530', adjust='qfq')
            if df is None or len(df) == 0:
                continue
            
            records = 0
            for _, row in df.iterrows():
                try:
                    d = row['日期'].strftime('%Y%m%d') if hasattr(row['日期'], 'strftime') else str(row['日期']).replace('-', '')
                    o = float(row['开盘'])
                    h = float(row['最高'])
                    l = float(row['最低'])
                    cl = float(row['收盘'])
                    pc = float(row.get('昨收', row.get('前收盘', cl)))
                    chg = float(row.get('涨跌幅', 0))
                    vol = int(float(row.get('成交量', 0)))
                    amt = float(row.get('成交额', 0))
                    tr = float(row.get('换手率', 0))
                    
                    c.execute("""INSERT IGNORE INTO stock_daily 
                        (stock_code, trade_date, open_price, high_price, low_price, close_price, pre_close, change_percent, volume, amount, turnover_rate)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (code, d, o, h, l, cl, pc, chg, vol, amt, tr))
                    records += 1
                except:
                    pass
            
            total_inserted += records
            # 每只Stock慢一点，避免被封
            time.sleep(0.3)
            
        except Exception as e:
            pass
    
    conn.commit()
    print(f"  累计插入: {total_inserted} 条")

conn.commit()
conn.close()
print(f"\n===== 采集完成! 共 {total_inserted} 条 =====")
