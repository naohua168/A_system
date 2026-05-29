"""将最新基金详情 CSV 更新到 MySQL（处理 code 格式不一致）"""
import pandas as pd
import pymysql
from pathlib import Path

def norm(code):
    """统一为整数形式，去除 .0 和零填充"""
    if pd.isna(code):
        return ""
    s = str(code).strip().replace(".0", "")
    return s

DATA_DIR = Path("/data/raw")
files = sorted(DATA_DIR.glob("fund_details_20260529_024824.csv"))
if not files:
    print("❌ 未找到 fund_details CSV")
    exit(1)

fp = str(files[-1])
df = pd.read_csv(fp)
print(f"📋 读取 {fp}: {len(df)} 条")

# 预读全部 DB 基金代码并建立映射
conn = pymysql.connect(host="mysql", port=3306, user="root",
                       password="hadoop123", database="stock_analysis",
                       charset="utf8mb4")
cursor = conn.cursor()
cursor.execute("SELECT fund_code FROM fund")
db_codes = {}
for row in cursor.fetchall():
    key = norm(row[0])
    if key:
        db_codes[key] = row[0]  # 原始 DB code

updated, not_found = 0, 0
for _, row in df.iterrows():
    csv_code = norm(row.get("fund_code", ""))
    if not csv_code or csv_code not in db_codes:
        not_found += 1
        continue
    
    mgr = str(row.get("manager", "")).strip() if pd.notna(row.get("manager")) else ""
    scale = float(row.get("scale", 0)) if pd.notna(row.get("scale")) else 0
    
    if not mgr and scale == 0:
        continue
    
    db_code = db_codes[csv_code]
    sql = "UPDATE fund SET manager=%s, scale=%s WHERE fund_code=%s"
    cursor.execute(sql, (mgr, scale, db_code))
    if cursor.rowcount > 0:
        updated += 1

conn.commit()
cursor.close()
conn.close()

print(f"✅ 已更新 {updated} 条 | 未匹配 {not_found} 条 | 总计 {len(df)} 条")
