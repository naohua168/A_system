"""
数据同步引擎 — 基于 StorageManager 的下一代同步器

替代 sync_to_mysql.py 的手动规则模式，使用 DataCatalog + StorageManager：
  1. 扫描 data/raw/ 目录下的 CSV 文件
  2. 根据文件名前缀匹配 DataCatalog 中定义的 storage.mysql_table
  3. 通过 StorageManager.write(mysql_table, df) 写入 MySQL
  4. 不依赖硬编码的 SYNC_RULES 和 mapper 函数
  5. 前端从 MySQL 读取（通过 Java API），与采集层完全解耦

用法:
    python scheduler/sync_engine.py             # 同步所有 CSV 到 MySQL
    python scheduler/sync_engine.py --loop 5    # 每5分钟同步一次
    python scheduler/sync_engine.py --dry-run   # 预览待同步文件
"""

import argparse
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import DATA_DIR
from pipeline.data_catalog import DATA_CATALOG
from storage.storage_manager import StorageManager

logger = logging.getLogger("data_collector.sync_engine")


class SyncEngine:
    """基于 DataCatalog 的自动同步引擎

    与旧 sync_to_mysql.py 的区别:
      - 旧: 硬编码 SYNC_RULES + 每类数据一个 mapper 函数
      - 新: 自动从 DataCatalog 读取 MySQL 表名映射，直接写入
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.storage = StorageManager() if not dry_run else None
        self._prefix_map = self._build_prefix_map()

    def _build_prefix_map(self) -> Dict[str, str]:
        """构建 csv_prefix → mysql_table 映射"""
        mapping = {}
        for dt in DATA_CATALOG:
            if dt.storage.csv_prefix and dt.storage.mysql_table:
                mapping[dt.storage.csv_prefix] = dt.storage.mysql_table
        return mapping

    def scan_csv_files(self) -> List[dict]:
        """扫描 data/raw/ 目录，识别可同步的 CSV 文件"""
        raw_dir = DATA_DIR
        if not raw_dir.exists():
            return []

        files = []
        for f in sorted(raw_dir.glob("*.csv")):
            fname = f.name
            for prefix, table in self._prefix_map.items():
                if fname.startswith(prefix):
                    files.append({
                        "path": str(f),
                        "name": fname,
                        "table": table,
                        "prefix": prefix,
                    })
                    break
        return files

    def sync_all(self) -> int:
        """同步所有待同步文件"""
        files = self.scan_csv_files()
        if not files:
            print("📭 没有发现待同步的 CSV 文件")
            return 0

        print(f"📦 发现 {len(files)} 个待同步文件")
        success = 0
        total_rows = 0

        for f in files:
            if self._sync_file(f):
                success += 1
                # 统计行数
                try:
                    df = pd.read_csv(f["path"])
                    if not df.empty:
                        total_rows += len(df)
                except Exception:
                    pass

        print(f"\n📊 完成: {success}/{len(files)} 成功, 共 {total_rows} 条记录")
        return success

    def _sync_file(self, file_info: dict) -> bool:
        """同步单个 CSV 文件"""
        fname = file_info["name"]
        table = file_info["table"]
        path = file_info["path"]

        try:
            df = pd.read_csv(path)
            if df.empty:
                print(f"   ⚠️  空文件: {fname}")
                return False

            if self.dry_run:
                print(f"   📋 [预览] {fname} → {table}: {len(df)} 条")
                return True

            written, total = self.storage.mysql.write(table, df)
            if written > 0:
                print(f"   ✅ {fname} → {table}: {written}/{total} 条")
            else:
                print(f"   ⚠️  {fname} → {table}: 写入0条(可能均为重复)")
            return written > 0 or total > 0

        except Exception as e:
            print(f"   ❌ {fname}: {e}")
            return False

    def close(self):
        if self.storage:
            self.storage.close()


def main():
    parser = argparse.ArgumentParser(
        description="📤 数据同步引擎 (基于 StorageManager + DataCatalog)"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔（分钟）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()
    engine = SyncEngine(dry_run=args.dry_run)

    def run_once():
        engine.sync_all()

    if args.loop > 0:
        print(f"🔄 定时同步启动，间隔 {args.loop} 分钟")
        while True:
            run_once()
            print(f"\n⏳ 等待 {args.loop} 分钟后下次同步...\n")
            time.sleep(args.loop * 60)
    else:
        run_once()

    engine.close()


if __name__ == "__main__":
    main()
