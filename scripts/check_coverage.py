import pymysql
conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4')
cur = conn.cursor()
total_stocks = 5544

tables = {
    'stock_daily': ('日K线', 'trade_date'),
    'stock_financial': ('财务数据', 'created_at'),
    'signal_concept_block': ('概念板块', 'created_at'),
    'signal_fund_flow': ('资金流向', 'trade_date'),
    'signal_dragon_tiger_detail': ('龙虎榜', 'trade_date'),
    'signal_lockup_detail': ('解禁', 'created_at'),
    'info_research_report': ('研报', 'publish_date'),
    'info_stock_news': ('个股新闻', 'publish_time'),
    'info_consensus_eps': ('一致预期', 'created_at'),
    'info_filing': ('公告', 'publish_date'),
}

for t, (label, date_col) in tables.items():
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(DISTINCT stock_code) FROM {t}")
    stocks = cur.fetchone()[0]
    try:
        cur.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {t}")
        dr = cur.fetchone()
        range_str = f"{dr[0]} ~ {dr[1]}"
    except:
        range_str = "N/A"
    print(f"{label:10s} ({t:28s}): {cnt:>8,}条  {stocks:>5d}只  范围: {range_str}")

# 检查基金数据
cur.execute("SELECT COUNT(*) FROM fund")
print(f"\n基金:     {cur.fetchone()[0]} 只")
cur.execute("SELECT COUNT(*), COUNT(DISTINCT fund_code) FROM fund_nav")
r = cur.fetchone()
print(f"基金净值: {r[0]}条,  {r[1]}只")
cur.execute("SELECT COUNT(*), COUNT(DISTINCT fund_code) FROM fund_holding")
r = cur.fetchone()
print(f"基金持仓: {r[0]}条,  {r[1]}只")

# 指数数据
cur.execute("SELECT COUNT(*) FROM market_index")
mi = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT index_code) FROM index_daily")
id_cnt = cur.fetchone()[0]
cur.execute("SELECT MIN(trade_date), MAX(trade_date) FROM index_daily")
idr = cur.fetchone()
print(f"\n指数: {mi} 个, K线{id_cnt}个 ({idr[0]} ~ {idr[1]})")

conn.close()
