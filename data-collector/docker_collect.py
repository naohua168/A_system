"""Docker 全量采集 — K线 + 资讯层全市场"""
import sys, time, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("docker_collect")

try:
    from config import MYSQL_CONFIG as _MC
    MYSQL_CFG = {
        "host": _MC["host"], "port": _MC["port"],
        "user": _MC["user"], "password": _MC["password"],
        "database": _MC["database"],
    }
except ImportError:
    MYSQL_CFG = {
        "host": "mysql", "port": 3306,
        "user": "root", "password": "hadoop123",
        "database": "stock_analysis",
    }
MAX_STOCKS = 100  # 先采前100只验证

try:
    import akshare as ak
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "akshare", "-q"])
    import akshare as ak

import pandas as pd
import pymysql

def db():
    return pymysql.connect(**MYSQL_CFG)

def get_codes():
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT stock_code FROM stock ORDER BY total_market_cap DESC")
    codes = [r[0] for r in cur.fetchall()]; cur.close(); conn.close()
    log.info("获取 %d 只股票", len(codes))
    return codes[:MAX_STOCKS]

def collect_kline(codes):
    log.info("=== K线采集 ===")
    all_data = []; ok = 0
    for i, code in enumerate(codes):
        try:
            suffix = "SH" if code[0] in ("6","9") else "SZ"
            df = ak.stock_zh_a_hist(symbol=f"{code}.{suffix}", period="daily",
                                    start_date="20250101", adjust="qfq")
            if not df.empty:
                df["stock_code"] = code
                df.rename(columns={"日期":"trade_date","开盘":"open","收盘":"close",
                    "最高":"high","最低":"low","成交量":"volume","成交额":"amount",
                    "涨跌幅":"change_pct","换手率":"turnover_pct"}, inplace=True)
                all_data.append(df); ok += 1
        except Exception as e:
            log.warning("  [%d/%d] %s: %s", i+1, len(codes), code, str(e)[:30])
        if (i+1)%20==0: log.info("  K线 %d/%d 成功%d", i+1, len(codes), ok)

    if not all_data: log.warning("K线0只成功"); return 0
    full = pd.concat(all_data, ignore_index=True)
    conn = db(); cur = conn.cursor()
    cur.execute("DELETE FROM stock_daily")
    written = 0
    for _, r in full.iterrows():
        try:
            cur.execute("INSERT INTO stock_daily (stock_code,trade_date,open_price,high_price,low_price,close_price,volume,amount,change_percent,turnover_rate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (r.stock_code, r.trade_date, r.open, r.high, r.low, r.close, r.volume, r.amount, r.change_pct, r.turnover_pct))
            written += 1
        except: pass
    conn.commit(); cur.close(); conn.close()
    log.info("K线写入 %d 行/%d 只", written, ok)
    return written

def collect_info(codes):
    log.info("=== 资讯层采集 ===")
    conn = db(); cur = conn.cursor()

    # 研报
    log.info("--- 研报 ---")
    cur.execute("DELETE FROM info_research_report")
    ok = 0
    for i, code in enumerate(codes):
        try:
            df = ak.stock_report_em(symbol=code)
            if not df.empty:
                for _, r in df.iterrows():
                    cur.execute("INSERT IGNORE INTO info_research_report (stock_code,title,org_name,rating) VALUES (%s,%s,%s,%s)",
                        (code, str(r.get("研报标题",""))[:200], str(r.get("机构名称","")), str(r.get("评级",""))))
                ok += 1
        except: pass
        if (i+1)%10==0: conn.commit(); log.info("  研报 %d/%d", i+1, len(codes))
    conn.commit(); log.info("研报 %d 只", ok)

    # 一致预期
    log.info("--- 一致预期EPS ---")
    cur.execute("DELETE FROM info_consensus_eps")
    ok = 0
    for i, code in enumerate(codes[:30]):
        try:
            df = ak.stock_profit_forecast(symbol=code)
            if not df.empty:
                for _, r in df.iterrows():
                    cur.execute("INSERT IGNORE INTO info_consensus_eps (stock_code,year,forecast_count,avg_eps) VALUES (%s,%s,%s,%s)",
                        (code, str(r.get("年度","")), int(r.get("预测机构数",0)), float(r.get("平均值",0))))
                ok += 1
        except: pass
    conn.commit(); log.info("EPS %d 只", ok)

    # 新闻
    log.info("--- 个股新闻 ---")
    cur.execute("DELETE FROM info_stock_news")
    ok = 0
    for i, code in enumerate(codes[:30]):
        try:
            df = ak.stock_news_em(symbol=code)
            if not df.empty:
                for _, r in df.iterrows():
                    cur.execute("INSERT IGNORE INTO info_stock_news (stock_code,title,publish_time) VALUES (%s,%s,%s)",
                        (code, str(r.get("标题",""))[:200], str(r.get("发布时间",""))))
                ok += 1
        except: pass
    conn.commit(); log.info("新闻 %d 只", ok)

    cur.close(); conn.close()

if __name__ == "__main__":
    t0 = time.time()
    codes = get_codes()
    collect_kline(codes)
    collect_info(codes)
    log.info("全部完成! 耗时 %d 秒", time.time()-t0)
