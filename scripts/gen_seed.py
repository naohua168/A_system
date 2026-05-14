import random, sys
random.seed(42)

stocks = [
    ('000001',12.00),('000002',16.50),('000333',66.80),('000651',41.20),
    ('000725',5.20),('000858',157.00),('002415',34.50),('002475',31.00),
    ('300750',200.00),('600000',8.20),('600036',37.00),('600276',46.50),
    ('600519',1690.00),('600887',28.50),('601012',26.00),('601166',18.50),
    ('601318',45.50),('601398',5.80),('601857',8.50),('603259',56.00),
]
dates = ['2026-04-29','2026-04-30','2026-05-06','2026-05-07','2026-05-08']
prev = {c: round(p*(1+random.uniform(-0.008,0.008)),2) for c,p in stocks}
rows = []
for code,base in stocks:
    pc = prev[code]
    for dt in dates:
        chg = random.uniform(-0.025,0.025)
        close = round(base*(1+chg),2)
        o = round(close*(1+random.uniform(-0.012,0.012)),2)
        h = round(max(o,close)*(1+random.uniform(0,0.015)),2)
        l = round(min(o,close)*(1-random.uniform(0,0.015)),2)
        cp = round((close-pc)/pc*100,4) if pc!=0 else 0
        vol = int(random.uniform(2000000,70000000)/max(base/50,0.1))
        amt = round(vol*close,2)
        tr = round(random.uniform(0.1,3.5),2)
        rows.append(f"('{code}','{dt}',{o},{h},{l},{close},{pc},{vol},{amt},{cp},{tr})")
        pc = close

# Write without BOM
with open(sys.stdout.buffer.fileno(), 'wb') as f:
    for line in ["DELETE FROM stock_daily WHERE trade_date >= '2026-04-29';",
                 "INSERT INTO stock_daily (stock_code,trade_date,open_price,high_price,low_price,close_price,pre_close,volume,amount,change_percent,turnover_rate) VALUES",
                 ",\n".join(rows)+";"]:
        f.write((line + '\n').encode('utf-8'))
