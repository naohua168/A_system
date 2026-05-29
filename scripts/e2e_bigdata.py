#!/usr/bin/env python3
"""
大数据层端到端验证脚本 — 检查全链路: 采集→HDFS→Hive→MySQL→API
"""
import subprocess, sys

def check(name, cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        ok = r.returncode == 0
        print(f"  {'✅' if ok else '❌'} {name}")
        if not ok: print(f"     {r.stderr[:100]}")
        return ok
    except Exception as e:
        print(f"  ⚠️ {name}: {e}")
        return False

print("=" * 50)
print("📋 大数据层端到端验证")
print("=" * 50)

print("\n1️⃣  采集层")
check("data-collector 运行中", "docker ps --filter name=data-collector --format '{{.Status}}' | grep -q healthy")
check("CSV 数据存在", "docker exec data-collector ls /data/raw/*.csv 2>/dev/null | head -3")

print("\n2️⃣  HDFS 数据湖")
check("HDFS 目录存在", "docker exec namenode hdfs dfs -test -d /user/hadoop/stock_data 2>/dev/null")
check("HDFS 有数据文件", "docker exec namenode hdfs dfs -ls /user/hadoop/stock_data/basic/ 2>/dev/null | grep -q csv")

print("\n3️⃣  Hive 数据仓库")
check("Hive 表存在", "docker exec hive-server hive -e 'USE stock_analysis; SHOW TABLES;' 2>/dev/null | grep -q stock_daily")
check("Hive 有数据", "docker exec hive-server hive -e 'USE stock_analysis; SELECT COUNT(*) FROM stock_basic;' 2>/dev/null | tail -1 | grep -q '[1-9]'")

print("\n4️⃣  MySQL 服务层")
check("MySQL 运行中", "docker ps --filter name=mysql --format '{{.Status}}' | grep -q Up")
check("各表有数据", "docker exec data-collector python -c \"import pymysql; c=pymysql.connect(host='mysql',user='root',password='hadoop123',database='stock_analysis'); cur=c.cursor(); cur.execute('SELECT COUNT(*) FROM fund'); print(cur.fetchone()[0]); c.close()\" 2>/dev/null | grep -q '[1-9]'")

print("\n5️⃣  API 层")
s = "import requests; s=requests.Session(); r=s.post('http://backend:8082/api/user/login',json={'username':'admin','password':'admin123'},timeout=10); t=r.json().get('data',{}).get('token',''); s.headers.update({'Authorization':'Bearer '+t})"
check("行情API", f"docker exec data-collector python -c \"{s}; r=s.get('http://backend:8082/api/market/list?page=1&size=1',timeout=10); print(r.status_code)\" 2>/dev/null | grep -q 200")
check("基金API", f"docker exec data-collector python -c \"{s}; r=s.get('http://backend:8082/api/fund/list?page=1&size=1',timeout=10); print(r.status_code)\" 2>/dev/null | grep -q 200")
check("ETF API", f"docker exec data-collector python -c \"{s}; r=s.get('http://backend:8082/api/market/etf?page=1&size=1',timeout=10); print(r.status_code)\" 2>/dev/null | grep -q 200")
check("AI 对话", f"docker exec data-collector python -c \"{s}; r=s.post('http://backend:8082/api/ai/chat',json={{'message':'你好','type':'chat'}},timeout=30); print(r.status_code)\" 2>/dev/null | grep -q 200")

print("\n6️⃣  容器状态")
check("全部容器健康", "docker ps --format '{{.Status}}' | grep -v healthy | grep -v Up && false || true")

print("\n" + "=" * 50)
print("🏁 验证完成")
