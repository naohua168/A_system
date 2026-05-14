"""
数据同步脚本：将 data-collector 采集的数据同步到后端 MySQL
打通数据采集 → 后端数据库的通道

用法:
    # 同步所有 CSV 到数据库
    python sync_to_mysql.py

    # 同步并显示处理详情
    python sync_to_mysql.py --verbose

    # 同步指定文件
    python sync_to_mysql.py --file data/raw/kline_688017_daily_20260513.csv

    # 仅预览（不执行插入）
    python sync_to_mysql.py --dry-run

    # 定时同步（每5分钟）
    python sync_to_mysql.py --loop 5
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd

from config import DATA_DIR


# ============================================================
# MySQL 连接配置（与后端 application.yml 一致）
# ============================================================
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "hadoop123",
    "database": "stock_analysis",
}

# ============================================================
# 文件 → 数据库表 映射规则
# ============================================================
SYNC_RULES = [
    {
        "prefix": "kline_",
        "table": "stock_daily",
        "columns": ["stock_code", "trade_date", "open_price", "close_price",
                     "high_price", "low_price", "volume", "amount", "change_percent"],
        "mapper": lambda df, fname: _map_kline(df, fname),
    },
    {
        "prefix": "realtime_",
        "table": "stock",
        "columns": ["stock_code", "stock_name", "pe", "pb", "total_market_cap",
                     "turnover_rate", "change_percent"],
        "mapper": lambda df, _: _map_realtime(df),
    },
    {
        "prefix": "fund_nav_",
        "table": "fund_nav",
        "columns": ["fund_code", "nav_date", "nav", "accumulated_nav", "daily_return"],
        "mapper": lambda df, fname: _map_fund_nav(df, fname),
    },
    # ==================== 信号层（a-stock-data 新增） ====================
    {
        "prefix": "hot_reason_",
        "table": "signal_hot_reason",
        "columns": ["trade_date", "stock_code", "stock_name", "reason",
                     "change_pct", "turnover_pct"],
        "mapper": lambda df, fname: _map_hot_reason(df, fname),
    },
    {
        "prefix": "northbound_",
        "table": "signal_northbound",
        "columns": ["trade_date", "hgt_yi", "sgt_yi"],
        "mapper": lambda df, fname: _map_northbound(df, fname),
    },
    {
        "prefix": "industry_compare_",
        "table": "signal_daily_industry",
        "columns": ["trade_date", "rank_num", "industry_name", "change_pct",
                     "turnover_yi", "net_inflow_yi", "up_count", "down_count", "leader"],
        "mapper": lambda df, fname: _map_industry(df, fname),
    },
]


def get_db_connection():
    """获取 MySQL 数据库连接"""
    try:
        import pymysql
        return pymysql.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            charset="utf8mb4",
        )
    except ImportError:
        print("⚠️  pymysql 未安装，执行: pip install pymysql")
        return None
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None


# ============================================================
# 数据映射函数
# ============================================================

def _map_kline(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """CSV K线 → stock_daily 表格式"""
    code_match = re.search(r"kline_(\w+)_", fname)
    stock_code = code_match.group(1) if code_match else ""

    records = []
    for _, row in df.iterrows():
        date = row.get("date", "")
        if isinstance(date, str):
            date = date.replace("-", "")
        records.append({
            "stock_code": stock_code,
            "trade_date": date,
            "open_price": row.get("open", 0),
            "close_price": row.get("close", 0),
            "high_price": row.get("high", 0),
            "low_price": row.get("low", 0),
            "volume": int(row.get("volume", 0)),
            "amount": float(row.get("amount", 0)),
            "change_percent": row.get("change_pct", 0),
        })
    return pd.DataFrame(records)


def _map_realtime(df: pd.DataFrame) -> pd.DataFrame:
    """实时行情 → stock 表格式"""
    records = []
    for _, row in df.iterrows():
        records.append({
            "stock_code": row.get("code", ""),
            "stock_name": row.get("name", ""),
            "pe": row.get("pe_ttm", 0),
            "pb": row.get("pb", 0),
            "total_market_cap": row.get("mcap_yi", 0),
            "turnover_rate": row.get("turnover_pct", 0),
            "change_percent": row.get("change_pct", 0),
        })
    return pd.DataFrame(records)


def _map_fund_nav(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """基金净值 → fund_nav 表格式"""
    code_match = re.search(r"fund_nav_(\w+)_", fname)
    fund_code = code_match.group(1) if code_match else ""

    records = []
    for _, row in df.iterrows():
        date = row.get("date", "")
        if isinstance(date, str):
            date = date.replace("-", "")
        records.append({
            "fund_code": fund_code,
            "nav_date": date,
            "nav": row.get("nav", 0),
            "accumulated_nav": row.get("accum_nav", 0),
            "daily_return": row.get("daily_change", 0),
        })
    return pd.DataFrame(records)


# ============================================================
# 信号层数据映射函数（a-stock-data 新增）
# ============================================================

def _map_hot_reason(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """题材归因 → signal_hot_reason 表格式"""
    records = []
    for _, row in df.iterrows():
        records.append({
            "trade_date": row.get("fetch_date", "").replace("-", ""),
            "stock_code": row.get("代码", ""),
            "stock_name": row.get("名称", ""),
            "reason": row.get("题材归因", ""),
            "change_pct": row.get("涨幅%", 0),
            "turnover_pct": row.get("换手率%", 0),
        })
    return pd.DataFrame(records)


def _map_northbound(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """北向资金 → signal_northbound 表格式
    取当日最后一条分钟数据作为日收盘数据
    """
    if df.empty:
        return pd.DataFrame()
    last_row = df.dropna().iloc[-1]
    return pd.DataFrame([{
        "trade_date": last_row.get("date", "").replace("-", "") or
                       last_row.get("time", "")[:10].replace("-", ""),
        "hgt_yi": last_row.get("hgt_yi", 0),
        "sgt_yi": last_row.get("sgt_yi", 0),
    }])


def _map_industry(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """行业对比 → signal_daily_industry 表格式"""
    records = []
    for i, row in df.iterrows():
        records.append({
            "trade_date": row.get("fetch_date", "").replace("-", ""),
            "rank_num": i + 1,
            "industry_name": row.get("name", ""),
            "change_pct": row.get("change_pct", 0),
            "turnover_yi": row.get("turnover_yi", 0),
            "net_inflow_yi": row.get("net_inflow_yi", 0),
            "up_count": row.get("up_count", 0),
            "down_count": row.get("down_count", 0),
            "leader": row.get("leader", ""),
        })
    return pd.DataFrame(records)


# ============================================================
# 同步处理器
# ============================================================

class DataSync:
    """数据同步器"""

    def __init__(self, verbose: bool = False, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.conn = None if dry_run else get_db_connection()
        self.total_inserted = 0

    def scan_csv_files(self) -> List[dict]:
        """扫描 data/raw 目录，识别可同步的 CSV 文件"""
        raw_dir = DATA_DIR
        if not raw_dir.exists():
            return []

        files = []
        for f in sorted(raw_dir.glob("*.csv")):
            fname = f.name
            for rule in SYNC_RULES:
                if fname.startswith(rule["prefix"]):
                    files.append({"path": str(f), "name": fname, "rule": rule})
                    break
        return files

    def sync_file(self, file_info: dict) -> bool:
        """同步单个 CSV 文件到数据库"""
        fname = file_info["name"]
        rule = file_info["rule"]
        path = file_info["path"]

        try:
            df = pd.read_csv(path)
            if df.empty:
                if self.verbose:
                    print(f"   ⚠️  空文件: {fname}")
                return False

            mapped = rule["mapper"](df, fname)
            if mapped.empty:
                return False

            # 去重：使用 INSERT IGNORE
            placeholders = ", ".join(["%s"] * len(mapped.columns))
            cols = ", ".join(mapped.columns)
            sql = f"INSERT IGNORE INTO {rule['table']} ({cols}) VALUES ({placeholders})"

            if self.dry_run:
                if self.verbose:
                    print(f"   📋 [预览] {fname} → {rule['table']}: {len(mapped)} 条")
                return True

            cursor = self.conn.cursor()
            values = [tuple(row) for row in mapped.values]
            cursor.executemany(sql, values)
            self.conn.commit()
            cursor.close()
            self.total_inserted += len(mapped)
            print(f"   ✅ {fname} → {rule['table']}: {len(mapped)} 条")
            return True

        except Exception as e:
            print(f"   ❌ {fname}: {e}")
            return False

    def sync_all(self) -> int:
        """同步所有待同步文件"""
        files = self.scan_csv_files()
        if not files:
            print("📭 没有发现待同步的 CSV 文件")
            return 0

        print(f"📦 发现 {len(files)} 个待同步文件\n")
        success = 0
        for f in files:
            if self.sync_file(f):
                success += 1
        print(f"\n📊 完成: {success}/{len(files)} 成功, 共 {self.total_inserted} 条记录")
        return success

    def close(self):
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="数据同步: CSV → MySQL")
    parser.add_argument("--file", type=str, help="同步指定文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔（分钟）")

    args = parser.parse_args()
    syncer = DataSync(verbose=args.verbose, dry_run=args.dry_run)

    def run_once():
        if args.file:
            # 同步单个文件
            fpath = Path(args.file)
            if not fpath.exists():
                print(f"❌ 文件不存在: {args.file}")
                return
            fname = fpath.name
            for rule in SYNC_RULES:
                if fname.startswith(rule["prefix"]):
                    syncer.sync_file({"path": str(fpath), "name": fname, "rule": rule})
                    break
            else:
                print(f"❌ 无法识别文件类型: {fname}")
        else:
            syncer.sync_all()

    if args.loop > 0:
        print(f"🔄 定时同步启动，间隔 {args.loop} 分钟")
        while True:
            run_once()
            print(f"\n⏳ 等待 {args.loop} 分钟后下次同步...\n")
            time.sleep(args.loop * 60)
    else:
        run_once()

    syncer.close()


if __name__ == "__main__":
    main()
