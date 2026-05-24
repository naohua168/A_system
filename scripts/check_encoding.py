#!/usr/bin/env python3
import pymysql
conn = pymysql.connect(host='localhost', port=3307, user='root', password='hadoop123', database='stock_analysis', charset='utf8mb4')
c = conn.cursor()

# 检查当前 HEX 值
c.execute("SELECT index_code, HEX(index_name), CHAR_LENGTH(index_name), index_name FROM market_index WHERE index_code IN ('000001','000688','399001','399006')")
print("=== 当前 index_name 状态 ===")
for row in c.fetchall():
    print(f"  {row[0]}: HEX={row[1]}, LEN={row[2]}")

# 强制用正确的 UTF-8 字符串重写
print("\n=== 修复名称 ===")
fixes = [
    ("000001", "上证指数"), ("399001", "深证成指"), ("399006", "创业板指"),
    ("000688", "科创50"), ("000300", "沪深300"), ("000016", "上证50"),
    ("399905", "中证500"), ("HSI", "恒生指数"), ("DJI", "道琼斯"),
    ("IXIC", "纳斯达克"), ("SPX", "标普500"),
]
for code, name in fixes:
    c.execute("UPDATE market_index SET index_name=%s WHERE index_code=%s", (name, code))
    print(f"  {code}: {name} -> affected {c.rowcount}")

c.execute("SELECT index_code, HEX(index_name), index_name FROM market_index WHERE index_code IN ('000001','000688','399001','399006')")
print("\n=== 修复后 ===")
for row in c.fetchall():
    print(f"  {row[0]}: HEX={row[1]}, name={row[2]}")

conn.commit()
c.close()
conn.close()
print("\nDONE")
