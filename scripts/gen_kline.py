"""为 HDFS/Hive 生成仿真日K线数据并上传到 WebHDFS"""
import csv, random, json, os, sys
from datetime import datetime, timedelta
from pyhive import hive

random.seed(42)

def trading_days(n=60):
    days = []
    d = datetime.now()
    while len(days) < n:
        if d.weekday() < 5:
            days.insert(0, d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return days

def simulate_kline(base_price, days_list):
    klines = []
    price = base_price
    for td in days_list:
        cp = random.uniform(-0.05, 0.05)
        close = round(price * (1 + cp), 2)
        close = max(close, 0.5)
        high = round(close * (1 + random.uniform(0, 0.03)), 2)
        low = round(close * (1 - random.uniform(0, 0.03)), 2)
        o = round(low + random.random() * (high - low), 2)
        volume = int(random.uniform(500000, 50000000))
        amount = round(volume * close / 100000000, 2)
        klines.append({
            "trade_date": td, "open": o, "high": high,
            "low": low, "close": close,
            "volume": volume, "amount": amount,
            "change_pct": round(cp * 100, 2)
        })
        price = close
    return klines

def webhdfs_upload(content, path):
    """通过 WebHDFS HTTP API 上传文件 (使用 hadoop 用户)"""
    import requests
    user = "hadoop"
    # Step 1: ensure parent dir exists
    parent = "/".join(path.split("/")[:-1])
    dir_url = f"http://namenode:9870/webhdfs/v1{parent}?op=MKDIRS&user.name={user}"
    requests.put(dir_url, timeout=10)

    url = f"http://namenode:9870/webhdfs/v1{path}?op=CREATE&overwrite=true&user.name={user}"
    r = requests.put(url, allow_redirects=False, timeout=10)
    if r.status_code not in (307, 201):
        print(f"  WebHDFS CREATE 失败: {r.status_code} {r.text[:100]}")
        return False
    loc = r.headers.get("Location")
    if not loc:
        print(f"  无跳转地址")
        return False
    # Step 2: actual upload to DataNode
    r2 = requests.put(loc, data=content.encode("utf-8-sig"),
                      headers={"Content-Type": "application/octet-stream"}, timeout=120)
    if r2.status_code in (201, 200):
        print(f"  ✅ 上传成功: {path}")
        return True
    else:
        print(f"  上传失败: {r2.status_code} {r2.text[:100]}")
        return False

def create_hive_table(cursor, ddl):
    for stmt in ddl.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"  Hive DDL 警告: {e}")

def main():
    print("连接 Hive...")
    conn = hive.connect(host="hive-server", port=10000)
    c = conn.cursor()
    c.execute("SELECT stock_code, stock_name FROM stock_basic LIMIT 500")
    stocks = [{"code": r[0], "name": r[1]} for r in c.fetchall()]
    c.close()
    print(f"获取 {len(stocks)} 只股票")

    days = trading_days(60)
    print(f"生成 {len(days)} 个交易日 K 线...")

    header = ["stock_code","stock_name","trade_date","open","high","low","close","volume","amount","change_pct"]
    lines = [",".join(header)]
    for s in stocks:
        base = random.uniform(3, 80)
        klines = simulate_kline(base, days)
        for k in klines:
            row = [s["code"], s["name"], k["trade_date"],
                   str(k["open"]), str(k["high"]), str(k["low"]), str(k["close"]),
                   str(k["volume"]), str(k["amount"]), str(k["change_pct"])]
            lines.append(",".join(row))

    content = "\n".join(lines)
    print(f"生成 {len(stocks) * len(days)} 行 K 线数据 ({len(content)} bytes)")

    # 上传到 HDFS
    print("\n上传到 HDFS...")
    webhdfs_upload(content, "/user/hadoop/stock_data/daily/daily_kline.csv")

    # 创建 Hive 外表
    print("\n创建/更新 Hive 表...")
    ddl = """
    CREATE EXTERNAL TABLE IF NOT EXISTS stock_daily (
        stock_code STRING, stock_name STRING, trade_date STRING,
        open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
        volume BIGINT, amount DOUBLE, change_pct DOUBLE
    )
    ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
    STORED AS TEXTFILE
    LOCATION '/user/hadoop/stock_data/daily'
    TBLPROPERTIES ('skip.header.line.count' = '1')
    """
    cc = conn.cursor()
    for stmt in ddl.split(";"):
        s = stmt.strip()
        if s:
            try:
                cc.execute(s)
            except Exception as e:
                print(f"  警告: {e}")
    cc.close()

    # 验证
    cc = conn.cursor()
    cc.execute("SELECT COUNT(*) FROM stock_daily")
    cnt = cc.fetchone()[0]
    print(f"\n✅ stock_daily 表验证: {cnt} 条记录")
    cc.close()
    conn.close()

if __name__ == "__main__":
    main()
