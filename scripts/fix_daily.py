import pymysql
conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# ====== 1. 填充龙虎榜简单表 ======
cur.execute("TRUNCATE signal_dragon_tiger")
cur.execute("""
    INSERT IGNORE INTO signal_dragon_tiger(trade_date, stock_code, stock_name, reason,
        change_pct, net_buy_wan, buy_wan, sell_wan, turnover_pct)
    SELECT trade_date, stock_code, stock_name, reason,
        change_pct, net_buy_wan, buy_wan, sell_wan, turnover_pct
    FROM signal_dragon_tiger_detail
""")
print(f"龙虎榜简单表: 填充{cur.rowcount}条")

# ====== 2. 检查hot-reason问题 ======
cur.execute("SELECT MAX(trade_date), COUNT(*) FROM signal_hot_reason")
max_date, total = cur.fetchone()
print(f"热点数据: {total}条, 最新日期: {max_date}")

# 检查API返回参数区别 - 2026-05-27是否真有数据
cur.execute("SELECT COUNT(*) FROM signal_hot_reason WHERE trade_date='2026-05-27'")
today_count = cur.fetchone()[0]
print(f"今天(2026-05-27)数据: {today_count}条")

cur.execute("SELECT COUNT(*) FROM signal_hot_reason WHERE trade_date='2026-05-26'")
yesterday_count = cur.fetchone()[0]
print(f"昨天(2026-05-26)数据: {yesterday_count}条")

conn.close()
print("完成!")
