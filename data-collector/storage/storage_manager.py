"""
统一存储管理器 — 数据持久化抽象层

职责：
  1. 提供统一的 write / read 接口，屏蔽后端差异
  2. 管理 MySQL / CSV / HDFS 三种存储后端
  3. 保证写入一致性（事务 + 幂等性）
  4. 前端/后端必须通过此层读取数据，与采集层完全解耦

设计原则：
  - 采集层 (adapters) 只管 fetch → 返回 DataFrame
  - 管道层 (pipeline) 编排 fetch → validate → store
  - 存储层 (storage) 只负责持久化读写
  - 前端/后端 API 只从存储层读，绝不直接调适配器
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import DATA_DIR, MYSQL_SYNC

logger = logging.getLogger("data_collector.storage")


# ============================================================
# 存储后端抽象
# ============================================================
class StorageBackend(ABC):
    """存储后端抽象接口"""

    @abstractmethod
    def write(self, table: str, df: pd.DataFrame, mode: str = "append") -> Tuple[int, int]:
        """写入数据，返回 (写入行数, 总行数)"""
        ...

    @abstractmethod
    def read(self, table: str, filters: Optional[Dict] = None,
             limit: int = 1000) -> pd.DataFrame:
        """读取数据"""
        ...

    @abstractmethod
    def get_latest(self, table: str, key_column: str, key_value: str,
                   limit: int = 100) -> pd.DataFrame:
        """获取某实体的最新N条记录"""
        ...


# ============================================================
# CSV 后端
# ============================================================
class CsvStorage(StorageBackend):
    """CSV 文件存储后端"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _filepath(self, table: str, suffix: str = "") -> Path:
        """生成 CSV 文件路径"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.base_dir / f"{table}{suffix}_{ts}.csv"

    def write(self, table: str, df: pd.DataFrame,
              mode: str = "append") -> Tuple[int, int]:
        if df.empty:
            return (0, 0)
        fp = self._filepath(table)
        df.to_csv(fp, index=False, encoding="utf-8-sig")
        logger.info("[CSV] %s → %s (%d rows)", table, fp.name, len(df))
        return (len(df), len(df))

    def read(self, table: str, filters: Optional[Dict] = None,
             limit: int = 1000) -> pd.DataFrame:
        files = sorted(self.base_dir.glob(f"{table}_*.csv"))
        if not files:
            return pd.DataFrame()
        # 默认读取最新的文件
        latest = files[-1]
        df = pd.read_csv(latest)
        if filters:
            for col, val in filters.items():
                if col in df.columns:
                    df = df[df[col] == val]
        return df.head(limit)

    def get_latest(self, table: str, key_column: str, key_value: str,
                   limit: int = 100) -> pd.DataFrame:
        files = sorted(self.base_dir.glob(f"{table}_*.csv"))
        if not files:
            return pd.DataFrame()
        latest = files[-1]
        df = pd.read_csv(latest)
        if key_column in df.columns:
            df = df[df[key_column] == key_value]
        return df.head(limit)


# ============================================================
# MySQL 后端
# ============================================================
class MysqlStorage(StorageBackend):
    """MySQL 数据库存储后端

    表名映射：
      - realtime_quotes → stock
      - history_kline   → stock_daily
      - 其他按 data_catalog 中 storage.mysql_table
    """

    _TABLE_MAP = {}  # data_type → mysql_table，由外部注入

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._conn = None
        self._connected = False

    def _get_connection(self):
        """获取 MySQL 连接（带重试）"""
        if self._conn is not None:
            try:
                self._conn.ping(reconnect=True)
                return self._conn
            except Exception:
                self._conn = None

        import pymysql
        import os
        cfg = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", "hadoop123"),
            "database": os.getenv("MYSQL_DB", "stock_analysis"),
            "charset": "utf8mb4",
            "connect_timeout": 10,
            "read_timeout": 30,
            "write_timeout": 30,
        }
        cfg.update(self.config)
        self._conn = pymysql.connect(**cfg)
        self._connected = True
        return self._conn

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def write(self, table: str, df: pd.DataFrame,
              mode: str = "append") -> Tuple[int, int]:
        if df.empty:
            return (0, 0)

        conn = self._get_connection()
        cursor = conn.cursor()
        total_rows = len(df)
        inserted = 0
        batch_size = MYSQL_SYNC.get("batch_size", 200)

        try:
            placeholders = ", ".join(["%s"] * len(df.columns))
            cols = ", ".join(df.columns)
            sql = f"INSERT IGNORE INTO {table} ({cols}) VALUES ({placeholders})"

            values = [tuple(row) for row in df.values]
            for start in range(0, total_rows, batch_size):
                batch = values[start:start + batch_size]
                cursor.executemany(sql, batch)
                conn.commit()
                inserted += len(batch)
        except Exception as e:
            conn.rollback()
            logger.error("[MySQL] 写入失败 %s: %s", table, e)
            return (0, total_rows)
        finally:
            cursor.close()

        logger.info("[MySQL] %s → %d/%d rows", table, inserted, total_rows)
        return (inserted, total_rows)

    def read(self, table: str, filters: Optional[Dict] = None,
             limit: int = 1000) -> pd.DataFrame:
        conn = self._get_connection()
        where_clause = ""
        if filters:
            conditions = [f"{k} = %s" for k in filters]
            where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"SELECT * FROM {table} {where_clause} ORDER BY created_at DESC LIMIT {limit}"
        try:
            with conn.cursor() as cursor:
                params = list(filters.values()) if filters else []
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                if not rows:
                    return pd.DataFrame()
                columns = [desc[0] for desc in cursor.description]
                return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.error("[MySQL] 读取失败 %s: %s", table, e)
            return pd.DataFrame()

    def get_latest(self, table: str, key_column: str, key_value: str,
                   limit: int = 100) -> pd.DataFrame:
        return self.read(
            table,
            filters={key_column: key_value},
            limit=limit,
        )


# ============================================================
# 统一存储管理器 — 对外暴露的 Facade
# ============================================================
class StorageManager:
    """存储管理器 — 统一的存储 Facade

    使用方式:
        sm = StorageManager()
        sm.write("realtime_quotes", df)
        df = sm.read("realtime_quotes", {"stock_code": "000001"})
    """

    def __init__(self):
        self._csv = CsvStorage()
        self._mysql = MysqlStorage()
        self._backends: Dict[str, StorageBackend] = {
            "csv": self._csv,
            "mysql": self._mysql,
        }

    @property
    def csv(self) -> CsvStorage:
        return self._csv

    @property
    def mysql(self) -> MysqlStorage:
        return self._mysql

    def write(self, table: str, df: pd.DataFrame,
              backends: Optional[List[str]] = None) -> Dict[str, Tuple[int, int]]:
        """写入所有指定的后端

        Args:
            table: 表名
            df: 数据
            backends: 后端列表, 默认 ["csv", "mysql"]
        Returns:
            {backend_name: (written, total)}
        """
        if backends is None:
            backends = ["csv", "mysql"]

        results = {}
        for name in backends:
            backend = self._backends.get(name)
            if backend:
                try:
                    results[name] = backend.write(table, df)
                except Exception as e:
                    logger.error("[%s] 写入失败: %s", name, e)
                    results[name] = (0, len(df))
        return results

    def read(self, table: str, filters: Optional[Dict] = None,
             limit: int = 1000, backend: str = "mysql") -> pd.DataFrame:
        """从指定后端读取数据

        默认从 MySQL 读取（前端统一读取路径）。
        仅调试或数据恢复时切换为 csv。
        """
        bk = self._backends.get(backend)
        if not bk:
            raise ValueError(f"不支持的存储后端: {backend}")
        return bk.read(table, filters, limit)

    def get_latest(self, table: str, key_column: str, key_value: str,
                   limit: int = 100, backend: str = "mysql") -> pd.DataFrame:
        bk = self._backends.get(backend)
        if not bk:
            raise ValueError(f"不支持的存储后端: {backend}")
        return bk.get_latest(table, key_column, key_value, limit)

    def close(self):
        self._mysql.close()
