"""检查所有数据表当前状态"""
import pymysql

conn = pymysql.connect(host="localhost", port=3307, user="root",
                       password="hadoop123", database="stock_analysis",
                       charset="utf8mb4")
cursor = conn.cursor()

tables = [
    "fund_holding", "fund", "fund_nav",
    "signal_concept_block", "signal_fund_flow",
    "signal_hot_reason", "signal_northbound", "signal_daily_industry",
    "signal_dragon_tiger_detail", "signal_lockup_detail",
    "stock", "stock_daily", "index_daily",
    "info_research_report", "info_consensus_eps", "info_stock_news",
    "info_cls_news", "info_global_news",
    "analysis_result",
    "market_index", "stock_financial",
]

total = 0
print(f"{'='*55}")
print(f"{'表名':25s} {'行数':>10s}")
print(f"{'='*55}")
for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        total += count
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {table:25s} {count:>10,}")
    except Exception as e:
        print(f"  ⚠️  {table:25s} ERROR: {str(e)[:30]}")

print(f"{'='*55}")
print(f"  📊 总计: {total:,} 行")
print(f"{'='*55}")
conn.close()
