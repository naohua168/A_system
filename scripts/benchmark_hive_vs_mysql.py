#!/usr/bin/env python3
"""
MySQL vs Hive ORC 查询性能对比（论文实验数据）
对比相同查询在两种引擎上的执行时间
"""
import subprocess, time, json

def docker_exec(container, cmd, timeout=120):
    full_cmd = f"docker exec {container} sh -c \"{cmd}\""
    t0 = time.time()
    r = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    elapsed = time.time() - t0
    return elapsed, r.stdout.strip(), r.returncode

def mysql_query(sql):
    return docker_exec("data-collector",
        f"python -c \"import pymysql; c=pymysql.connect(host='mysql',user='root',password='hadoop123',database='stock_analysis'); cur=c.cursor(); cur.execute('''{sql}'''); print(cur.fetchone()[0]); c.close()\"")

def hive_query(sql):
    return docker_exec("hive-server",
        f"hive -e 'USE stock_analysis; {sql}' 2>/dev/null | tail -1")

queries = [
    ("COUNT(*)", "SELECT COUNT(*) FROM stock_daily"),
    ("行业涨跌排行", """
        SELECT s.industry, AVG(d.change_percent)
        FROM stock_daily d JOIN stock s ON d.stock_code = s.stock_code
        WHERE d.trade_date = (SELECT MAX(trade_date) FROM stock_daily)
        GROUP BY s.industry
    """),
    ("某股票全部K线", "SELECT COUNT(*) FROM stock_daily WHERE stock_code = '000001'"),
    ("涨幅TOP10", """
        SELECT stock_code, MAX(change_percent)
        FROM stock_daily
        WHERE trade_date >= '2026-01-01'
        GROUP BY stock_code ORDER BY 2 DESC LIMIT 10
    """),
]

print("=" * 60)
print("📊 MySQL vs Hive ORC 性能对比")
print("=" * 60)
print(f"{'查询':20s} {'MySQL(秒)':>10s} {'Hive(秒)':>10s} {'加速比':>8s}")
print("-" * 60)

for name, sql in queries:
    mysql_t, mysql_r, _ = mysql_query(sql.replace("'", "\\'"))
    hive_t, hive_r, _ = hive_query(sql)
    ratio = mysql_t / hive_t if hive_t > 0 else 0
    print(f"{name:20s} {mysql_t:>8.2f}s  {hive_t:>8.2f}s  {ratio:>6.1f}x")
    print(f"  MySQL结果: {mysql_r[:60]}")
    print(f"  Hive结果:  {hive_r[:60]}")

print("=" * 60)
print("🏁 对比完成")
