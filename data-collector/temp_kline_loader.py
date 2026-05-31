#!/usr/bin/env python3
"""
1. 创建 stock_daily 表
2. 从腾讯API获取近500天K线数据并插入
（默认只采集关键股票，可指定 --all 全市场）
"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import sys, argparse, time, logging
from datetime import datetime
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from collectors.stock_list import StockListProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger("kline_loader")

# MySQL 连接
import pymysql
DB = {"host": "localhost", "port": 3307, "user": "root",
      "password": "hadoop123", "database": "stock_analysis",
      "charset": "utf8mb4", "connect_timeout": 10, "autocommit": False}

DDL = """CREATE TABLE IF NOT EXISTS `stock_daily` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `open_price` DECIMAL(10,2) DEFAULT NULL COMMENT '开盘价',
    `high_price` DECIMAL(10,2) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(10,2) DEFAULT NULL COMMENT '最低价',
    `close_price` DECIMAL(10,2) DEFAULT NULL COMMENT '收盘价',
    `pre_close` DECIMAL(10,2) DEFAULT NULL COMMENT '昨收价',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量（股）',
    `amount` DECIMAL(20,2) DEFAULT NULL COMMENT '成交额（元）',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `turnover_rate` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率(%)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_date` (`stock_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日K线数据表';"""

sess = requests.Session()
sess.trust_env = False

def get_prefix(code):
    return {"6":"sh","5":"sh","9":"sh","0":"sz","3":"sz","2":"sz","4":"bj","8":"bj"}.get(code[0], "sh")

def fetch_tencent_kline(code, days=500):
    prefix = get_prefix(code)
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{days},qfq"
    try:
        r = sess.get(url, timeout=15, proxies={"http":None,"https":None})
        data = r.json()
        if not data or data.get("error"):
            return []
        klines = (data.get("data", {}).get(f"{prefix}{code}", {}).get("day", []) or
                  data.get("data", {}).get(f"{prefix}{code}", {}).get("qfqday", []))
        return klines
    except Exception as e:
        log.warning(f"  {code} API error: {e}")
        return []

def parse_and_insert(cur, klines, code):
    """解析腾讯K线并批量插入"""
    rows = []
    for k in klines:
        if len(k) < 6: continue
        date_str = str(k[0]).replace("-", "")
        try:
            rows.append((
                code, date_str,
                float(k[1]), float(k[2]),  # open, close
                float(k[4]), float(k[3]),  # low, high
                0.0,  # pre_close
                int(float(k[5])) if k[5] else 0,  # volume
                0.0, 0.0, 0.0,  # amount, change, turnover
            ))
        except: continue
    if not rows: return 0
    sql = """INSERT IGNORE INTO stock_daily
        (stock_code,trade_date,open_price,high_price,low_price,close_price,
         pre_close,volume,amount,change_percent,turnover_rate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    cur.executemany(sql, rows)
    return len(rows)

def fix_change_percent(cur):
    """修复涨跌幅"""
    cur.execute("""
        UPDATE stock_daily t1
        JOIN stock_daily t2 ON t1.stock_code = t2.stock_code
            AND t2.trade_date = DATE_SUB(t1.trade_date, INTERVAL 1 DAY)
        SET t1.change_percent = ROUND((t1.close_price - t2.close_price)/t2.close_price*100, 2),
            t1.pre_close = t2.close_price
        WHERE t1.change_percent = 0 AND t1.pre_close = 0
    """)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="全市场采集")
    parser.add_argument("--codes", type=str, default="000001,600519,000333,002415,300059,600036,601318,600900,000858,002594",
                        help="逗号分隔的股票代码")
    args = parser.parse_args()

    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    # 1. 创建表
    log.info("创建 stock_daily 表...")
    cur.execute(DDL)
    conn.commit()
    log.info("表创建完成")

    # 2. 获取股票列表
    if args.all:
        log.info("获取全市场股票列表...")
        provider = StockListProvider()
        codes = provider.get_all_codes(force_refresh=True)
        log.info(f"共 {len(codes)} 只股票")
    else:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        log.info(f"采集 {len(codes)} 只关键股票: {codes}")

    # 3. 逐个采集
    total = 0
    for code in codes:
        log.info(f"采集 {code}...")
        klines = fetch_tencent_kline(code)
        if not klines or len(klines) < 5:
            log.warning(f"  {code} 无数据")
            time.sleep(0.3)
            continue
        n = parse_and_insert(cur, klines, code)
        conn.commit()
        total += n
        if n:
            log.info(f"  ✅ {code}: {n} 条 (最新: {klines[-1][0]})")
        time.sleep(0.3)

    # 4. 修复涨跌幅
    log.info("修复涨跌幅...")
    fix_change_percent(cur)
    conn.commit()

    # 5. 统计
    cur.execute("SELECT COUNT(*), MAX(trade_date), MIN(trade_date), COUNT(DISTINCT stock_code) FROM stock_daily")
    r = cur.fetchone()
    log.info(f"完成！共 {r[0]} 条K线, {r[3]} 只股票, {r[1]} ~ {r[2]}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
