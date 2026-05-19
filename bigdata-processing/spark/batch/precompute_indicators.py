"""
K 线技术指标预计算 — 从 stock_daily 批量计算 MA/MACD/RSI/KDJ/布林带

两种运行模式:
  1. Spark 模式 (默认): pyspark DataFrame API + MySQL JDBC
  2. Pandas 模式 (--no-spark): 纯 Pandas 本地计算，无 Spark 依赖

用法:
  # Spark 模式（需配置 pyspark + mysql connector）
  python precompute_indicators.py --mode daily

  # Pandas 模式（本地调试）
  python precompute_indicators.py --mode daily --no-spark --limit 100

输出表（MySQL）:
  precomputed_ma_signal    — MA5/10/20/60 + 金叉/死叉
  precomputed_macd         — DIF/DEA/MACD
  precomputed_rsi          — RSI6/12/24
  precomputed_bollinger    — 中轨/上轨/下轨/带宽/%B
  precomputed_kdj          — K/D/J

与 L3 DataLoader.PRECOMPUTED_TABLES 的表名严格对齐。
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("precompute")

# ============================================================
# 指标计算（Pandas 向量化实现）
# ============================================================

def compute_ma(df, periods=None):
    """移动平均线: MA5/MA10/MA20/MA60 + 金叉/死叉信号"""
    if periods is None:
        periods = [5, 10, 20, 60]
    import pandas as pd
    result = df[["stock_code", "trade_date"]].copy()
    for p in periods:
        result[f"ma{p}"] = df["close"].rolling(window=p).mean().round(2)
    # 金叉/死叉 (MA5 × MA20)
    result["crossover_signal"] = "none"
    ma5 = df["close"].rolling(5).mean()
    ma20 = df["close"].rolling(20).mean()
    result.loc[ma5 > ma20, "crossover_signal"] = "golden"
    result.loc[ma5 < ma20, "crossover_signal"] = "death"
    return result


def compute_macd(df, fast=12, slow=26, signal=9):
    """MACD: DIF/DEA/MACD柱"""
    import pandas as pd
    result = df[["stock_code", "trade_date"]].copy()
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    result["dif"] = (ema_fast - ema_slow).round(4)
    result["dea"] = result["dif"].ewm(span=signal, adjust=False).mean().round(4)
    result["macd"] = (2 * (result["dif"] - result["dea"])).round(4)
    return result


def compute_rsi(df):
    """RSI: RSI6/RSI12/RSI24 (Wilders平滑)"""
    import pandas as pd
    import numpy as np
    result = df[["stock_code", "trade_date"]].copy()
    for period, col_name in [(6, "rsi6"), (12, "rsi12"), (24, "rsi24")]:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        result[col_name] = (100 - (100 / (1 + rs))).round(2)
    result = result.fillna(0)
    return result


def compute_bollinger(df, period=20, std_mult=2.0):
    """布林带: 中轨/上轨/下轨/带宽/%B"""
    import pandas as pd
    import numpy as np
    result = df[["stock_code", "trade_date"]].copy()
    result["boll_mid"] = df["close"].rolling(window=period).mean().round(2)
    std = df["close"].rolling(window=period).std()
    result["boll_up"] = (result["boll_mid"] + std_mult * std).round(2)
    result["boll_down"] = (result["boll_mid"] - std_mult * std).round(2)
    bandwidth = (result["boll_up"] - result["boll_down"]) / result["boll_mid"].replace(0, float("nan"))
    result["boll_width"] = (bandwidth * 100).round(2)
    result["boll_pb"] = (
        (df["close"] - result["boll_down"]) / (result["boll_up"] - result["boll_down"]).replace(0, 1)
    ).round(4)
    result = result.fillna(0)
    return result


def compute_kdj(df, n=9, m1=3, m2=3):
    """KDJ: K/D/J"""
    import pandas as pd
    import numpy as np
    result = df[["stock_code", "trade_date"]].copy()
    low_n = df["low"].rolling(window=n).min()
    high_n = df["high"].rolling(window=n).max()
    rsv = ((df["close"] - low_n) / (high_n - low_n).replace(0, float("nan")) * 100)
    result["k"] = rsv.ewm(alpha=1/m1, adjust=False).mean().round(2)
    result["d"] = result["k"].ewm(alpha=1/m2, adjust=False).mean().round(2)
    result["j"] = (3 * result["k"] - 2 * result["d"]).round(2)
    result = result.fillna(50.0)
    return result


# ============================================================
# MySQL 读写
# ============================================================

def _get_mysql():
    """获取 MySQL 连接（L2 独立，不依赖 L3）"""
    import os, pymysql
    candidates = [
        {"host": os.getenv("MYSQL_HOST", "localhost"), "port": int(os.getenv("MYSQL_PORT", "3306"))},
        {"host": "localhost", "port": 3306},
        {"host": "localhost", "port": 3307},
        {"host": "mysql", "port": 3306},
    ]
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "hadoop123")
    database = os.getenv("MYSQL_DB", "stock_analysis")
    for cfg in candidates:
        try:
            return pymysql.connect(host=cfg["host"], port=cfg["port"],
                                   user=user, password=password,
                                   database=database, charset="utf8mb4",
                                   connect_timeout=5, read_timeout=10)
        except Exception:
            continue
    raise ConnectionError("MySQL 连接失败，请确认数据库已启动")


def read_stock_daily(limit: int = 0) -> "pd.DataFrame":
    """从 MySQL 读取日 K 线数据"""
    import pandas as pd
    conn = _get_mysql()
    sql = """
        SELECT stock_code, trade_date, open_price as `open`,
               high_price as high, low_price as low,
               close_price as `close`, volume, amount
        FROM stock_daily
        ORDER BY stock_code, trade_date ASC
    """
    df = pd.read_sql(sql, conn)
    if limit > 0:
        df = df.head(limit)
    conn.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    return df


def write_precomputed(table: str, df: "pd.DataFrame", batch_size: int = 500) -> int:
    """写入 MySQL 预计算表"""
    import pandas as pd
    import pymysql
    conn = _get_mysql()
    cursor = conn.cursor()

    if df.empty:
        conn.close()
        return 0

    df = df.where(pd.notnull(df), None)
    cols = ", ".join(df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql = f"REPLACE INTO {table} ({cols}) VALUES ({placeholders})"

    values = [tuple(row) for row in df.values]
    inserted = 0
    for start in range(0, len(values), batch_size):
        batch = values[start:start + batch_size]
        try:
            cursor.executemany(sql, batch)
            conn.commit()
            inserted += len(batch)
        except Exception as e:
            conn.rollback()
            logger.warning("  [%s] 批量写入失败: %s", table, e)

    cursor.close()
    conn.close()
    return inserted


# ============================================================
# 主流程
# ============================================================

INDICATORS = {
    "precomputed_ma_signal": compute_ma,
    "precomputed_macd": compute_macd,
    "precomputed_rsi": compute_rsi,
    "precomputed_bollinger": compute_bollinger,
    "precomputed_kdj": compute_kdj,
}

TABLE_COLUMN_MAP = {
    "precomputed_ma_signal": "stock_code, trade_date, ma5, ma10, ma20, ma60, crossover_signal",
    "precomputed_macd": "stock_code, trade_date, dif, dea, macd",
    "precomputed_rsi": "stock_code, trade_date, rsi6, rsi12, rsi24",
    "precomputed_bollinger": "stock_code, trade_date, boll_mid, boll_up, boll_down, boll_width, boll_pb",
    "precomputed_kdj": "stock_code, trade_date, k, d, j",
}


def ensure_tables():
    """确保预计算表存在（如不存在则创建）"""
    conn = _get_mysql()
    cursor = conn.cursor()

    ddl_statements = [
        """CREATE TABLE IF NOT EXISTS precomputed_ma_signal (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            trade_date VARCHAR(10) NOT NULL,
            ma5 DECIMAL(12,4) DEFAULT 0,
            ma10 DECIMAL(12,4) DEFAULT 0,
            ma20 DECIMAL(12,4) DEFAULT 0,
            ma60 DECIMAL(12,4) DEFAULT 0,
            crossover_signal VARCHAR(10) DEFAULT 'none',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_date (stock_code, trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS precomputed_macd (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            trade_date VARCHAR(10) NOT NULL,
            dif DECIMAL(12,4) DEFAULT 0,
            dea DECIMAL(12,4) DEFAULT 0,
            macd DECIMAL(12,4) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_date (stock_code, trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS precomputed_rsi (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            trade_date VARCHAR(10) NOT NULL,
            rsi6 DECIMAL(12,4) DEFAULT 0,
            rsi12 DECIMAL(12,4) DEFAULT 0,
            rsi24 DECIMAL(12,4) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_date (stock_code, trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS precomputed_bollinger (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            trade_date VARCHAR(10) NOT NULL,
            boll_mid DECIMAL(12,4) DEFAULT 0,
            boll_up DECIMAL(12,4) DEFAULT 0,
            boll_down DECIMAL(12,4) DEFAULT 0,
            boll_width DECIMAL(12,4) DEFAULT 0,
            boll_pb DECIMAL(12,4) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_date (stock_code, trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS precomputed_kdj (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            trade_date VARCHAR(10) NOT NULL,
            k DECIMAL(12,4) DEFAULT 0,
            d DECIMAL(12,4) DEFAULT 0,
            j DECIMAL(12,4) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_date (stock_code, trade_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS precomputed_yearly_return (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            trade_year INT NOT NULL,
            yearly_return DECIMAL(12,4) DEFAULT 0,
            rank_num INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_code_year (stock_code, trade_year)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS precomputed_correlation (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            stock_code_a VARCHAR(10) NOT NULL,
            stock_code_b VARCHAR(10) NOT NULL,
            correlation DECIMAL(12,4) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_pair (stock_code_a, stock_code_b)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]

    for ddl in ddl_statements:
        try:
            cursor.execute(ddl)
            conn.commit()
        except Exception as e:
            logger.warning("建表失败: %s", e)

    cursor.close()
    conn.close()
    logger.info("预计算表创建/确认完成")


def main():
    parser = argparse.ArgumentParser(description="K线技术指标预计算")
    parser.add_argument("--mode", choices=["daily", "full", "single"],
                        default="daily", help="运行模式")
    parser.add_argument("--limit", type=int, default=0,
                        help="限制处理的股票数 (0=全部)")
    parser.add_argument("--code", default="", help="单只股票代码 (single 模式)")
    parser.add_argument("--days", type=int, default=365,
                        help="K线回溯天数")
    parser.add_argument("--batch", type=int, default=500,
                        help="MySQL写入批次大小")
    parser.add_argument("--ensure-tables", action="store_true",
                        help="仅建表，不计算")
    args = parser.parse_args()

    # 确保表存在
    ensure_tables()
    if args.ensure_tables:
        return

    # 读取 K 线数据
    logger.info("读取 stock_daily 数据...")
    import pandas as pd
    full_kline = read_stock_daily(limit=args.limit)
    if full_kline.empty:
        logger.error("stock_daily 无数据，请先运行 K 线采集")
        return

    # 确定待处理的股票
    stock_codes = sorted(full_kline["stock_code"].unique().tolist())
    if args.mode == "single" and args.code:
        stock_codes = [args.code]
    elif args.limit > 0:
        stock_codes = stock_codes[:args.limit]

    logger.info("待处理股票: %d 只, K线总行数: %d", len(stock_codes), len(full_kline))

    # 逐股票计算并写入
    t_start = time.time()
    total_rows = 0

    for i, code in enumerate(stock_codes):
        t0 = time.time()
        kline = full_kline[full_kline["stock_code"] == code].copy()
        if kline.empty:
            continue

        try:
            # 计算全部 5 种指标
            for table, compute_fn in INDICATORS.items():
                result = compute_fn(kline)
                # 过滤掉前 60 个 NaN 行（窗口预热）
                result = result.iloc[60:].reset_index(drop=True)
                if not result.empty:
                    rows = write_precomputed(table, result, args.batch)
                    total_rows += rows

            elapsed = time.time() - t0
            if (i + 1) % 10 == 0:
                rate = (i + 1) / (time.time() - t_start)
                remaining = (len(stock_codes) - i - 1) / rate if rate > 0 else 0
                logger.info("[%d/%d] %s ✅ (%.1fs) | 速率 %.1f只/秒 | 预计剩余 %.0fs",
                            i + 1, len(stock_codes), code, elapsed, rate, remaining)
            elif elapsed > 1.0:
                logger.info("[%d/%d] %s ✅ (%.1fs)", i + 1, len(stock_codes), code, elapsed)

        except Exception as e:
            logger.error("[%d/%d] %s 💥 %s", i + 1, len(stock_codes), code, e)

    total_elapsed = time.time() - t_start
    logger.info("=" * 55)
    logger.info("  预计算完成")
    logger.info("  股票: %d 只", len(stock_codes))
    logger.info("  总写入: %d 行", total_rows)
    logger.info("  耗时: %.1fs (%.1f 分钟)", total_elapsed, total_elapsed / 60)
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
