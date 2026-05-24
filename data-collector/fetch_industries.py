#!/usr/bin/env python3
"""从新浪获取行业数据并写入 stock.industry"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import re, requests, pymysql, time
from collections import defaultdict

sess = requests.Session(); sess.trust_env = False

# 连接MySQL
conn = pymysql.connect(host='mysql', port=3306, user='root', password='hadoop123',
                       database='stock_analysis', charset='utf8mb4')
cur = conn.cursor()

# 方案A: 从新浪行业板块成分股列表获取
print("=== 方案A: 新浪行业成分股 ===")
BASE = "http://vip.stock.finance.sina.com.cn/q/go.php/vIndustryRank/kind/gjsws/index.phtml"
r = sess.get(BASE, timeout=15, proxies={"http":None,"https":None})
industries = re.findall(r'id=(\d+).kind=gjsws[^>]*>([^<]+)<', r.text.replace('&','.'))
print(f"发现 {len(industries)} 个行业板块")

stock_industry = {}
for id_, name in industries[:10]:  # 仅取前10个行业（足够验证）
    url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Industry_StockList.tagList?tag={id_}&num=200"
    try:
        r2 = sess.get(url, timeout=10, proxies={"http":None,"https":None})
        items = re.findall(r'"code":"([^"]+)"', r2.text)
        for code in items:
            stock_industry[code.zfill(6)] = name
        print(f"  {name}: {len(items)} 只股票")
        time.sleep(0.5)
    except Exception as e:
        print(f"  {name}: {e}")

# 写入 MySQL
updated = 0
for code, ind in stock_industry.items():
    cur.execute("UPDATE stock SET industry=%s WHERE stock_code=%s", (ind, code))
    updated += cur.rowcount

print(f"\n行业归属写入完成: {updated} 行")
print(f"覆盖 {len(stock_industry)} 个股票代码")

num_with = cur.execute("SELECT COUNT(*) FROM stock WHERE industry IS NOT NULL AND industry != ''")
print(f"stock表已有行业的股票数: {cur.fetchone()[0]}")

conn.commit()
cur.close(); conn.close()
print("✅ 完成")
