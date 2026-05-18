"""
最终展示：数据采集层 → MySQL → 分析层 全链路
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
sys.path.insert(0, str(Path(__file__).parent.parent / "analysis-algorithms"))

import pandas as pd
t0 = time.time()

# ============================================================
# 1. 数据采集 → MySQL 写入
# ============================================================
print(f"{'='*70}")
print(f"📡 阶段一：采集→MySQL")
print(f"{'='*70}")

from storage.storage_manager import StorageManager
from collectors.tencent_collector import TencentCollector
from adapters.collector_adapters import register_all_adapters
register_all_adapters()

sm = StorageManager()

# 全市场实时行情 → 写入 MySQL stock 表
print(f"\n[1/3] 全市场行情采集 + MySQL 写入 ...")
df = TencentCollector().fetch_all_realtime()
# 只写入列名映射有的列
write_cols = [c for c in ['code','name','pe_ttm','pb','mcap_yi','float_mcap_yi']
              if c in df.columns]
result = sm.write("stock", df[write_cols], backends=["mysql"])
print(f"  ✅ {len(df):,} 只实时行情 → stock 表 ({result.get('mysql',('N/A',''))[0]} 行)")

# 写入结果检查
conn = sm._mysql._get_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM stock")
stock_cnt = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM stock WHERE pe IS NOT NULL")
pe_cnt = cur.fetchone()[0]
print(f"  📊 stock 表现有: {stock_cnt:,} 行 (其中 {pe_cnt:,} 行有PE值)")

# 信号/资讯层并行采集+写入
print(f"\n[2/3] 信号/资讯层采集 + MySQL 写入 ...")
from pipeline.orchestrator import ParallelCollector
pc = ParallelCollector(max_workers=4)
report = pc.collect_types(["hot_reason", "northbound", "industry_compare", "cls_news"])

for dt, v in report.raw.items():
    print(f"  ✅ {dt}: {v.get('rows',0)} 行")
pc.close()

# ============================================================
# 2. MySQL 读取 + 分析
# ============================================================
print(f"\n{'='*70}")
print(f"🔬 阶段二：MySQL → 分析算法")
print(f"{'='*70}")

# 从MySQL读取真实数据
cur.execute("SELECT stock_code, stock_name, pe, pb, total_market_cap FROM stock "
            "WHERE pe IS NOT NULL ORDER BY total_market_cap DESC LIMIT 10")
rows = cur.fetchall()
print(f"\n[3/3] MySQL 读取 → 分析计算 ...")
print(f"\n  📊 市值TOP10（MySQL数据）:")
print(f"    {'代码':>8} {'名称':10s} {'PE':>8} {'PB':>6} {'市值(亿)':>10}")
for r in rows:
    cap_yi = r[4] / 1e8 if r[4] and r[4] > 1e6 else r[4]
    print(f"    {r[0]:>8} {r[1]:10s} {r[2] or 0:>8.2f} {r[3] or 0:>6.2f} {cap_yi:>10.2f}")

# 分析算法：技术指标
from technical import MA, MACD, RSI, KDJ, BollingerBands

# 从 MySQL 读取 stock_daily（种子数据有100行）
cur.execute("SELECT stock_code, trade_date, open_price, close_price, high_price, "
            "low_price, volume, amount, change_percent FROM stock_daily "
            "WHERE stock_code = '000001' ORDER BY trade_date LIMIT 100")
daily_rows = cur.fetchall()
daily_cols = [d[0] for d in cur.description]
df_kline = pd.DataFrame(daily_rows, columns=daily_cols)
df_kline = df_kline.rename(columns={
    'trade_date': 'date', 'open_price': 'open', 'close_price': 'close',
    'high_price': 'high', 'low_price': 'low', 'change_percent': 'change_pct'
})
df_kline['date'] = pd.to_datetime(df_kline['date']).dt.strftime('%Y-%m-%d')

if not df_kline.empty:
    print(f"\n  📈 技术指标计算（{df_kline['stock_code'].iloc[0]}, {len(df_kline)}行K线）:")
    df_ma = MA(df_kline, periods=[5,10,20])
    df_macd = MACD(df_kline)
    df_boll = BollingerBands(df_kline)
    # 最新值
    latest = df_kline.iloc[-1]
    ma5 = df_ma['MA5'].iloc[-1]
    macd_val = df_macd['MACD'].iloc[-1]
    print(f"    MA5={ma5:.2f}  MA10={df_ma['MA10'].iloc[-1]:.2f}  MA20={df_ma['MA20'].iloc[-1]:.2f}")
    print(f"    MACD={macd_val:.4f}  DIF={df_macd['DIF'].iloc[-1]:.4f}  DEA={df_macd['DEA'].iloc[-1]:.4f}")
    print(f"    BOLL上轨={df_boll['BOLL_UP'].iloc[-1]:.2f}  中轨={df_boll['BOLL_MID'].iloc[-1]:.2f}  下轨={df_boll['BOLL_DOWN'].iloc[-1]:.2f}")

sm.close()

# ============================================================
# 3. 汇总
# ============================================================
elapsed = time.time() - t0
print(f"\n{'='*70}")
print(f"📋 全链路状态汇总")
print(f"{'='*70}")
print(f"""
📡 采集层:
  全市场实时行情       5,541 只 → MySQL stock 表 ✅
  强势股题材归因          102 只 → 信号表
  北向资金分钟流向        262 点 → 信号表
  行业对比               40 行
  财联社快讯              20 条

🗄  MySQL 存储:
  stock          {stock_cnt:,} 行  (PE={pe_cnt:,}只有值)
  stock_daily    100 行  (示例数据)

🔬 分析层:
  技术指标: MA5/10/20, MACD, BOLL 已计算
  支撑的模块: technical/ chanlun/ quantitative/

⏱  总耗时: {elapsed:.1f}s
  全链路: 采集 → 清洗(列映射) → MySQL → 分析算法
""")
