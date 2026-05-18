"""
数据同步脚本：将 data-collector 采集的数据同步到后端 MySQL
打通数据采集 → 后端数据库的通道

重构要点:
  - 事务安全: 每文件单事务，失败全量回滚
  - 分批插入: 控制 batch_size 防止大事务
  - 连接健康检查: 插入前自动重连
  - 前置数据校验: 空值/类型/范围检查
  - 去重确保幂等: INSERT IGNORE + 日期代码联合主键

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
import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd

from config import DATA_DIR, MYSQL_SYNC

logger = logging.getLogger("data_collector.sync")

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
    # ==================== 资讯层（a-stock-data 迁移合并：研报+新闻+公告） ====================
    {
        "prefix": "research_reports_",
        "table": "info_research_report",
        "columns": ["stock_code", "title", "publish_date", "org_name", "rating",
                     "predict_eps_this_year", "predict_eps_next_year", "info_code", "page_url", "source"],
        "mapper": lambda df, fname: _map_research_report(df),
    },
    {
        "prefix": "consensus_eps_",
        "table": "info_consensus_eps",
        "columns": ["stock_code", "year", "forecast_count", "min_eps", "avg_eps", "max_eps", "industry_avg"],
        "mapper": lambda df, fname: _map_consensus_eps(df, fname),
    },
    {
        "prefix": "stock_news_",
        "table": "info_stock_news",
        "columns": ["stock_code", "title", "publish_time", "content_summary", "source", "url"],
        "mapper": lambda df, fname: _map_stock_news(df, fname),
    },
    {
        "prefix": "cls_news_",
        "table": "info_cls_news",
        "columns": ["title", "publish_time", "content", "source", "url"],
        "mapper": lambda df, fname: _map_cls_news(df),
    },
    {
        "prefix": "global_news_",
        "table": "info_global_news",
        "columns": ["title", "publish_time", "summary", "source"],
        "mapper": lambda df, fname: _map_global_news(df),
    },
    {
        "prefix": "filings_",
        "table": "info_filing",
        "columns": ["stock_code", "title", "publish_date", "filing_type", "market", "content_summary", "url"],
        "mapper": lambda df, fname: _map_filings(df, fname),
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
    """获取 MySQL 数据库连接（带重试）"""
    max_retries = MYSQL_SYNC.get("max_retries", 2)
    delay = MYSQL_SYNC.get("reconnect_delay", 3)
    timeout = MYSQL_SYNC.get("connection_timeout", 10)

    for attempt in range(max_retries + 1):
        try:
            import pymysql
            conn = pymysql.connect(
                host=MYSQL_CONFIG["host"],
                port=MYSQL_CONFIG["port"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                charset="utf8mb4",
                connect_timeout=timeout,
            )
            return conn
        except ImportError:
            print("⚠️  pymysql 未安装，执行: pip install pymysql")
            return None
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️  数据库连接失败 (第{attempt+1}次): {e}，{delay}s 后重试...")
                time.sleep(delay)
            else:
                print(f"❌ 数据库连接失败 ({max_retries+1}次): {e}")
                return None
    return None


def check_connection(conn) -> bool:
    """检查连接是否有效，无效时重连"""
    if conn is None:
        return False
    try:
        conn.ping(reconnect=True)
        return True
    except Exception:
        return False


# ============================================================
# 数据校验函数
# ============================================================

def _validate_kline_row(row: dict) -> bool:
    """校验单条 K 线数据的合法性"""
    required = ["stock_code", "trade_date", "open_price", "close_price",
                "high_price", "low_price", "volume", "amount"]
    for field in required:
        if not row.get(field) and row.get(field) != 0:
            logger.warning("[校验] K线数据缺少字段 '%s': %s", field, row)
            return False
    date_str = str(row.get("trade_date", ""))
    if not re.match(r"^\d{8}$", date_str):
        logger.warning("[校验] K线日期格式非法: %s", date_str)
        return False
    # 价格逻辑校验: high >= low, close 在范围内
    try:
        o, h, l, c = float(row["open_price"]), float(row["high_price"]), float(row["low_price"]), float(row["close_price"])
        if h < l:
            logger.warning("[校验] K线 high < low: %s", row)
            return False
        if any(v < 0 for v in [o, h, l, c]):
            logger.warning("[校验] K线价格负数: %s", row)
            return False
    except (TypeError, ValueError):
        return False
    return True


def _validate_mapped_data(df: pd.DataFrame, rule: dict, fname: str) -> pd.DataFrame:
    """校验映射后的 DataFrame，过滤非法行"""
    if df.empty:
        return df
    before = len(df)
    # 去重 (基于所有列)
    df = df.drop_duplicates()
    # 过滤空主键
    if "stock_code" in df.columns:
        df = df[df["stock_code"].notna() & (df["stock_code"] != "")]
    if "trade_date" in df.columns:
        df = df[df["trade_date"].notna()]
    after = len(df)
    if before != after:
        logger.info("   [校验] %s: %d → %d 行 (过滤 %d 行)", fname, before, after, before - after)
    return df


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
        record = {
            "stock_code": stock_code,
            "trade_date": date,
            "open_price": float(row.get("open", 0)),
            "close_price": float(row.get("close", 0)),
            "high_price": float(row.get("high", 0)),
            "low_price": float(row.get("low", 0)),
            "volume": int(row.get("volume", 0)),
            "amount": float(row.get("amount", 0)),
            "change_percent": float(row.get("change_pct", 0)),
        }
        if _validate_kline_row(record):
            records.append(record)
    return pd.DataFrame(records)


def _map_realtime(df: pd.DataFrame) -> pd.DataFrame:
    """实时行情 → stock 表格式"""
    records = []
    for _, row in df.iterrows():
        records.append({
            "stock_code": row.get("code", ""),
            "stock_name": row.get("name", ""),
            "pe": float(row.get("pe_ttm", 0)),
            "pb": float(row.get("pb", 0)),
            "total_market_cap": float(row.get("mcap_yi", 0)),
            "turnover_rate": float(row.get("turnover_pct", 0)),
            "change_percent": float(row.get("change_pct", 0)),
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
            "nav": float(row.get("nav", 0)),
            "accumulated_nav": float(row.get("accum_nav", 0)),
            "daily_return": float(row.get("daily_change", 0)),
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
            "trade_date": str(row.get("fetch_date", "")).replace("-", ""),
            "stock_code": str(row.get("代码", "")),
            "stock_name": str(row.get("名称", "")),
            "reason": str(row.get("题材归因", "")),
            "change_pct": float(row.get("涨幅%", 0)),
            "turnover_pct": float(row.get("换手率%", 0)),
        })
    return pd.DataFrame(records)


def _map_northbound(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """北向资金 → signal_northbound 表格式
    取当日最后一条分钟数据作为日收盘数据
    """
    if df.empty:
        return pd.DataFrame()
    last_row = df.dropna().iloc[-1]
    date_val = str(last_row.get("date", "")).replace("-", "") or \
               str(last_row.get("time", ""))[:10].replace("-", "")
    if not re.match(r"^\d{8}$", date_val):
        logger.warning("[北向] 日期格式异常: %s", date_val)
        return pd.DataFrame()
    return pd.DataFrame([{
        "trade_date": date_val,
        "hgt_yi": float(last_row.get("hgt_yi", 0)),
        "sgt_yi": float(last_row.get("sgt_yi", 0)),
    }])


def _map_industry(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """行业对比 → signal_daily_industry 表格式"""
    records = []
    for i, row in df.iterrows():
        records.append({
            "trade_date": str(row.get("fetch_date", "")).replace("-", ""),
            "rank_num": i + 1,
            "industry_name": str(row.get("name", "")),
            "change_pct": float(row.get("change_pct", 0)),
            "turnover_yi": float(row.get("turnover_yi", 0)),
            "net_inflow_yi": float(row.get("net_inflow_yi", 0)),
            "up_count": int(row.get("up_count", 0)),
            "down_count": int(row.get("down_count", 0)),
            "leader": str(row.get("leader", "")),
        })
    return pd.DataFrame(records)


# ============================================================
# 资讯层数据映射函数（a-stock-data 迁移合并：研报+新闻+公告）
# ============================================================

def _map_research_report(df: pd.DataFrame) -> pd.DataFrame:
    """研报列表 → info_research_report 表格式"""
    records = []
    for _, row in df.iterrows():
        records.append({
            "stock_code": str(row.get("stock_code", "")),
            "title": str(row.get("title", "")),
            "publish_date": str(row.get("publish_date", ""))[:10].replace("-", ""),
            "org_name": str(row.get("org_name", "")),
            "rating": str(row.get("rating", "")),
            "predict_eps_this_year": float(row.get("predict_eps_this_year") or 0),
            "predict_eps_next_year": float(row.get("predict_eps_next_year") or 0),
            "info_code": str(row.get("info_code", "")),
            "page_url": str(row.get("page_url", "")),
            "source": str(row.get("source", "")),
        })
    return pd.DataFrame(records)


def _map_consensus_eps(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """一致预期EPS → info_consensus_eps 表格式"""
    code_match = re.search(r"consensus_eps_(\w+)_", fname)
    stock_code = code_match.group(1) if code_match else ""

    records = []
    for _, row in df.iterrows():
        records.append({
            "stock_code": stock_code or str(row.get("code", "")),
            "year": str(row.get("年度", row.get("year", ""))),
            "forecast_count": int(row.get("预测机构数", row.get("forecast_count", 0))),
            "min_eps": float(row.get("最小值", row.get("min_eps", 0))),
            "avg_eps": float(row.get("均值", row.get("avg_eps", 0))),
            "max_eps": float(row.get("最大值", row.get("max_eps", 0))),
            "industry_avg": float(row.get("行业平均数", row.get("industry_avg", 0))),
        })
    return pd.DataFrame(records)


def _map_stock_news(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """个股新闻 → info_stock_news 表格式"""
    code_match = re.search(r"stock_news_(\w+)_", fname)
    stock_code = code_match.group(1) if code_match else ""

    records = []
    for _, row in df.iterrows():
        records.append({
            "stock_code": stock_code or str(row.get("code", "")),
            "title": str(row.get("title", row.get("标题", ""))),
            "publish_time": str(row.get("publish_time", row.get("发布时间", "")))[:19],
            "content_summary": str(row.get("content", row.get("内容", "")))[:500],
            "source": str(row.get("source", "东方财富")),
            "url": str(row.get("url", row.get("链接", ""))),
        })
    return pd.DataFrame(records)


def _map_cls_news(df: pd.DataFrame) -> pd.DataFrame:
    """财联社快讯 → info_cls_news 表格式"""
    records = []
    for _, row in df.iterrows():
        records.append({
            "title": str(row.get("title", row.get("标题", ""))),
            "publish_time": str(row.get("publish_time", row.get("发布时间", "")))[:19],
            "content": str(row.get("content", row.get("内容", "")))[:1000],
            "source": "财联社",
            "url": str(row.get("url", "")),
        })
    return pd.DataFrame(records)


def _map_global_news(df: pd.DataFrame) -> pd.DataFrame:
    """全球资讯 → info_global_news 表格式"""
    records = []
    for _, row in df.iterrows():
        records.append({
            "title": str(row.get("title", row.get("标题", ""))),
            "publish_time": str(row.get("publish_time", row.get("发布时间", "")))[:19],
            "summary": str(row.get("content", row.get("摘要", "")))[:500],
            "source": str(row.get("source", "东方财富")),
        })
    return pd.DataFrame(records)


def _map_filings(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """巨潮公告 → info_filing 表格式"""
    code_match = re.search(r"filings_(\w+)_", fname)
    stock_code = code_match.group(1) if code_match else ""

    records = []
    for _, row in df.iterrows():
        records.append({
            "stock_code": stock_code or str(row.get("code", "")),
            "title": str(row.get("title", row.get("标题", ""))),
            "publish_date": str(row.get("publish_date", row.get("公告日期", "")))[:10].replace("-", ""),
            "filing_type": str(row.get("filing_type", row.get("公告类别", "公告"))),
            "market": str(row.get("market", "")),
            "content_summary": str(row.get("content", row.get("内容", "")))[:500],
            "url": str(row.get("url", row.get("链接", ""))),
        })
    return pd.DataFrame(records)


# ============================================================
# 同步处理器
# ============================================================

class DataSync:
    """数据同步器 — 事务安全版"""

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
        """同步单个 CSV 文件到数据库（事务安全）"""
        fname = file_info["name"]
        rule = file_info["rule"]
        path = file_info["path"]

        try:
            df = pd.read_csv(path)
            if df.empty:
                if self.verbose:
                    print(f"   ⚠️  空文件: {fname}")
                return False

            # 数据映射
            mapped = rule["mapper"](df, fname)
            if mapped.empty:
                if self.verbose:
                    print(f"   ⚠️  映射后无有效数据: {fname}")
                return False

            # 前置校验
            mapped = _validate_mapped_data(mapped, rule, fname)
            if mapped.empty:
                if self.verbose:
                    print(f"   ⚠️  校验后无有效数据: {fname}")
                return False

            # 构建 INSERT IGNORE 语句（幂等去重）
            placeholders = ", ".join(["%s"] * len(mapped.columns))
            cols = ", ".join(mapped.columns)
            sql = f"INSERT IGNORE INTO {rule['table']} ({cols}) VALUES ({placeholders})"

            if self.dry_run:
                if self.verbose:
                    print(f"   📋 [预览] {fname} → {rule['table']}: {len(mapped)} 条")
                return True

            # 连接健康检查
            if not check_connection(self.conn):
                print(f"   ⚠️  连接失效，尝试重连...")
                self.conn = get_db_connection()
                if not self.conn:
                    print(f"   ❌ 重连失败，跳过 {fname}")
                    return False

            # 分批插入（控制事务大小）
            cursor = self.conn.cursor()
            batch_size = MYSQL_SYNC.get("batch_size", 200)
            values = [tuple(row) for row in mapped.values]
            total_rows = len(values)
            inserted = 0
            try:
                for start in range(0, total_rows, batch_size):
                    batch = values[start:start + batch_size]
                    cursor.executemany(sql, batch)
                    self.conn.commit()
                    inserted += len(batch)
            except Exception as e:
                # 事务回滚
                self.conn.rollback()
                print(f"   ❌ 事务回滚 [{fname}]: {e}")
                return False
            finally:
                cursor.close()

            self.total_inserted += inserted
            print(f"   ✅ {fname} → {rule['table']}: {inserted}/{total_rows} 条")
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
            try:
                self.conn.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="数据同步: CSV → MySQL (事务安全版)")
    parser.add_argument("--file", type=str, help="同步指定文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔（分钟）")

    args = parser.parse_args()
    syncer = DataSync(verbose=args.verbose, dry_run=args.dry_run)

    def run_once():
        if args.file:
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
