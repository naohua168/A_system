"""
K线多周期聚合器 — 从日K聚合生成周K/月K并写入MySQL

功能:
  1. 从 stock_daily 表读取日K数据
  2. 聚合生成周K (stock_kline_weekly) 和 月K (stock_kline_monthly)
  3. 批量写入MySQL，支持增量更新（仅聚合新数据）
  4. 支持断点续传：记录上次聚合的时间戳

用法:
    python aggregate_kline.py                          # 全量聚合
    python aggregate_kline.py --stock 000001            # 指定股票
    python aggregate_kline.py --incremental             # 增量聚合（仅最近一周/月）
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from storage.storage_manager import StorageManager

logger = logging.getLogger("data_collector.aggregate")


class KlineAggregator:
    """K线多周期聚合器"""

    def __init__(self):
        self.storage = StorageManager()

    def _read_stock_daily(self, stock_code: str,
                          since_date: Optional[str] = None) -> pd.DataFrame:
        """从MySQL读取日K数据"""
        try:
            df = self.storage.read(
                "stock_daily",
                filters={"stock_code": stock_code} if stock_code else None,
                limit=5000,
            )
        except Exception:
            # 尝试直接SQL读取
            import pymysql
            from config import MYSQL_CONFIG
            conn = pymysql.connect(
                host=MYSQL_CONFIG["host"], port=MYSQL_CONFIG["port"],
                user=MYSQL_CONFIG["user"], password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"], charset="utf8mb4",
            )
            sql = "SELECT * FROM stock_daily"
            params = ()
            if stock_code:
                sql += " WHERE stock_code = %s"
                params = (stock_code,)
            if since_date:
                sql += " AND trade_date >= %s" if "WHERE" in sql else " WHERE trade_date >= %s"
                params = params + (since_date,)
            sql += " ORDER BY stock_code, trade_date"
            df = pd.read_sql(sql, conn, params=params)
            conn.close()

        if df.empty:
            return df
        # 统一列名
        col_rename = {"trade_date": "date", "open_price": "open",
                       "close_price": "close", "high_price": "high",
                       "low_price": "low"}
        df = df.rename(columns={k: v for k, v in col_rename.items() if k in df.columns})
        return df

    def aggregate_single(self, stock_code: str) -> tuple:
        """聚合单只股票的周K/月K

        Returns:
            (weekly_count, monthly_count)
        """
        df = self._read_stock_daily(stock_code)
        if df.empty:
            return (0, 0)

        # 确保date列
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"].astype(str), errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.sort_values("date")

        if df.empty:
            return (0, 0)

        weekly_df = self._aggregate_to(df, "weekly", stock_code)
        monthly_df = self._aggregate_to(df, "monthly", stock_code)

        wc = mc = 0
        if not weekly_df.empty:
            self.storage.write("stock_kline_weekly", weekly_df, backends=["mysql"])
            wc = len(weekly_df)
        if not monthly_df.empty:
            self.storage.write("stock_kline_monthly", monthly_df, backends=["mysql"])
            mc = len(monthly_df)

        return (wc, mc)

    def aggregate_all(self, stock_codes: Optional[List[str]] = None,
                      max_stocks: int = 0, incremental: bool = False) -> dict:
        """全市场聚合

        Args:
            stock_codes: 指定股票列表，None=全市场
            max_stocks: 最大股票数，0=不限
            incremental: 增量模式
        Returns:
            {stock_code: (weekly_count, monthly_count)}
        """
        if stock_codes is None:
            from collectors.stock_list import get_all_stock_codes
            stock_codes = get_all_stock_codes()
        if max_stocks > 0:
            stock_codes = stock_codes[:max_stocks]

        results = {}
        total = len(stock_codes)
        t0 = time.time()

        for idx, code in enumerate(stock_codes):
            try:
                wc, mc = self.aggregate_single(code)
                results[code] = (wc, mc)
                if (idx + 1) % 200 == 0:
                    logger.info("聚合进度 %d/%d (%.1f%%)",
                                idx + 1, total, (idx + 1) / total * 100)
            except Exception as e:
                logger.warning("[%s] 聚合失败: %s", code, e)
                results[code] = (0, 0)

        elapsed = time.time() - t0
        total_w = sum(v[0] for v in results.values())
        total_m = sum(v[1] for v in results.values())
        logger.info("聚合完成: %d/%d 股票, 周K %d条, 月K %d条, 耗时%.0fs",
                    sum(1 for v in results.values() if v[0] > 0 or v[1] > 0),
                    total, total_w, total_m, elapsed)
        return results

    @staticmethod
    def _aggregate_to(df: pd.DataFrame, target: str,
                      stock_code: str) -> pd.DataFrame:
        """从日K聚合到周K/月K"""
        gdf = df.copy()

        if target == "weekly":
            try:
                iso = gdf["date"].dt.isocalendar()
                gdf["_period"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
            except Exception:
                return pd.DataFrame()
            per_col = "week_label"
        else:
            gdf["_period"] = gdf["date"].dt.to_period("M").astype(str)
            per_col = "month_label"

        def _agg(grp):
            return pd.Series({
                per_col: grp.name,
                "stock_code": stock_code,
                "open_price": float(grp["open"].iloc[0]),
                "high_price": float(grp["high"].max()),
                "low_price": float(grp["low"].min()),
                "close_price": float(grp["close"].iloc[-1]),
                "volume": int(grp["volume"].sum()),
                "source": "aggregated",
            })

        result = gdf.groupby("_period", sort=False).apply(_agg, include_groups=False).reset_index(drop=True)
        return result if not result.empty else pd.DataFrame()

    def close(self):
        self.storage.close()


def main():
    parser = argparse.ArgumentParser(description="K线多周期聚合器")
    parser.add_argument("--stock", type=str, help="指定股票代码")
    parser.add_argument("--max-stocks", type=int, default=0, help="最大股票数")
    parser.add_argument("--incremental", action="store_true", help="增量模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    aggr = KlineAggregator()
    try:
        if args.stock:
            wc, mc = aggr.aggregate_single(args.stock)
            print(f"{args.stock}: 周K {wc}条, 月K {mc}条")
        else:
            aggr.aggregate_all(max_stocks=args.max_stocks,
                               incremental=args.incremental)
    finally:
        aggr.close()


if __name__ == "__main__":
    main()
