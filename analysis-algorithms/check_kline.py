"""检查 stock_daily 表数据"""
import sys
sys.path.insert(0, "f:/bs/A_system/analysis-algorithms")
from data.loader import DataLoader

dl = DataLoader()
conn = dl._get_mysql()

with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM stock_daily")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_daily")
    distinct_codes = cur.fetchone()[0]
    cur.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily")
    min_d, max_d = cur.fetchone()
    cur.execute("""
        SELECT stock_code, COUNT(*) as cnt,
               MIN(trade_date) as first, MAX(trade_date) as last
        FROM stock_daily GROUP BY stock_code
        ORDER BY cnt DESC LIMIT 10
    """)
    top = cur.fetchall()
    cur.execute("""
        SELECT stock_code, COUNT(*) as cnt,
               MIN(trade_date) as first, MAX(trade_date) as last
        FROM stock_daily GROUP BY stock_code
        ORDER BY cnt ASC LIMIT 10
    """)
    bottom = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM stock")
    total_stocks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM stock_daily WHERE stock_code='600519'")
    k600519 = cur.fetchone()[0]

print(f"=== stock_daily 表数据概况 ===")
print(f"全市场股票: {total_stocks} 只")
print(f"有 K 线数据: {distinct_codes} 只 (覆盖率 {distinct_codes/total_stocks*100:.1f}%)")
print(f"总记录数: {total:,} 条")
print(f"日期范围: {min_d} ~ {max_d}")
print(f"600519 记录: {k600519} 条")
print()

print(f"K 线最多的 10 只股票:")
print(f"{'代码':>8s} {'条数':>6s} {'起始':>12s} {'截止':>12s}")
for r in top:
    print(f"{r[0]:>8s} {r[1]:>6d} {str(r[2]):>12s} {str(r[3]):>12s}")

print(f"\nK 线最少的 10 只股票:")
print(f"{'代码':>8s} {'条数':>6s} {'起始':>12s} {'截止':>12s}")
for r in bottom:
    print(f"{r[0]:>8s} {r[1]:>6d} {str(r[2]):>12s} {str(r[3]):>12s}")
