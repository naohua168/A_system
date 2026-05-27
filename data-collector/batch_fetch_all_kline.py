#!/usr/bin/env python3
"""
全市场批量采集近2年日K线数据
数据源: 腾讯财经API (qt.gtimg.cn + web.ifzq.gtimg.cn)
"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import sys, time, socket as _socket, logging, json
from datetime import datetime, timedelta
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from collectors.stock_list import StockListProvider

try: _socket.gethostbyname("mysql"); DB_HOST = "mysql"; DB_PORT = 3306
except: DB_HOST = "localhost"; DB_PORT = 3307

import pymysql

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger("batch_kline")

DB = {"host": DB_HOST, "port": DB_PORT, "user": "root",
      "password": "hadoop123", "database": "stock_analysis",
      "charset": "utf8mb4", "connect_timeout": 10, "autocommit": False}

sess = requests.Session()
sess.trust_env = False

def get_prefix(code):
    """腾讯API前缀"""
    return {"6":"sh","5":"sh","9":"sh","0":"sz","3":"sz","2":"sz","4":"bj","8":"bj"}.get(code[0], "sh")

def fetch_tencent_kline(code, days=500):
    """从腾讯财经获取历史日K线
    API: http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz000001,day,,,500,qfq
    """
    prefix = get_prefix(code)
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{days},qfq"
    try:
        r = sess.get(url, timeout=15, proxies={"http":None,"https":None})
        data = r.json()
        if not data or data.get("error"):
            return []
        klines = data.get("data", {}).get(f"{prefix}{code}", {}).get("day", []) or \
                 data.get("data", {}).get(f"{prefix}{code}", {}).get("qfqday", [])
        return klines
    except Exception as e:
        log.warning(f"  {code} API error: {e}")
        return []

def parse_kline(klines, code):
    """解析腾讯K线格式: [date,open,close,high,low,volume]"""
    result = []
    for k in klines:
        if len(k) < 6:
            continue
        date_str = str(k[0]).replace("-", "")
        result.append((
            code, date_str,
            float(k[1]), float(k[2]),  # open, close
            float(k[4]), float(k[3]),  # low, high
            0.0,  # pre_close
            int(float(k[5])) if k[5] else 0,  # volume
            0.0, 0.0, 0.0,  # amount, change, turnover
        ))
    return result

def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    # 获取全市场股票
    log.info("获取全市场股票列表...")
    provider = StockListProvider()
    all_codes = provider.get_all_codes(force_refresh=True)
    log.info(f"共 {len(all_codes)} 只股票")

    # 已有数据统计
    cur.execute("SELECT stock_code, COUNT(*) FROM stock_daily GROUP BY stock_code")
    existing = {r[0]: r[1] for r in cur.fetchall()}
    need = [c for c in all_codes if existing.get(c, 0) < 200]
    log.info(f"已有充足数据: {len(all_codes)-len(need)}, 需补采: {len(need)}")

    total = 0
    fail_count = 0

    for idx, code in enumerate(need):
        klines = fetch_tencent_kline(code, days=500)
        if not klines or len(klines) < 10:
            fail_count += 1
            if fail_count > 50:  # 连续失败太多说明网络问题
                log.warning(f"连续失败过多，暂停30秒后重试...")
                time.sleep(30)
                fail_count = 0
            time.sleep(0.5)
            continue

        fail_count = 0
        rows = parse_kline(klines, code)
        if not rows:
            continue

        sql = """INSERT IGNORE INTO stock_daily
            (stock_code,trade_date,open_price,high_price,low_price,close_price,
             pre_close,volume,amount,change_percent,turnover_rate)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        cur.executemany(sql, rows)
        conn.commit()
        total += len(rows)

        if (idx + 1) % 100 == 0:
            cur.execute("SELECT COUNT(DISTINCT stock_code), COUNT(*) FROM stock_daily")
            codes_done, rows_done = cur.fetchone()
            log.info(f"进度 {idx+1}/{len(need)}: {codes_done}只股票, {rows_done}条")

        time.sleep(0.3)

    # 修复涨跌幅
    log.info("修复涨跌幅...")
    cur.execute("""
        UPDATE stock_daily t1
        JOIN stock_daily t2 ON t1.stock_code = t2.stock_code
            AND t2.trade_date = DATE_SUB(t1.trade_date, INTERVAL 1 DAY)
        SET t1.change_percent = ROUND((t1.close_price - t2.close_price)/t2.close_price*100,2),
            t1.pre_close = t2.close_price
        WHERE t1.change_percent = 0 AND t1.pre_close = 0
    """)
    conn.commit()

    cur.execute("SELECT COUNT(DISTINCT stock_code), COUNT(*) FROM stock_daily")
    codes_done, rows_done = cur.fetchone()
    log.info(f"完成！{codes_done}只股票, {rows_done}条日K数据")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
