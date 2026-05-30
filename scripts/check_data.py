"""检查股票数据是否为真实采集"""
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3307, user='root', password='hadoop123', database='stock_analysis')
c = conn.cursor()

# Check 平安银行 (000001)
c.execute("SELECT stock_code, trade_date, close_price, open_price, high_price, low_price, change_percent FROM stock_daily WHERE stock_code='000001' ORDER BY trade_date DESC LIMIT 5")
print("=== 平安银行 (000001) 最新数据 ===")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]} o={r[3]} h={r[4]} l={r[5]} c={r[2]} chg={r[6]}%")

# Check stock_000001 data count
c.execute("SELECT COUNT(DISTINCT stock_code), COUNT(*) FROM stock_daily")
r = c.fetchone()
print(f"\n总计: {r[0]} 只股票, {r[1]} 条记录")

# Check if there are records beyond the simulated dates
c.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily")
r = c.fetchone()
print(f"日期范围: {r[0]} ~ {r[1]}")

conn.close()
