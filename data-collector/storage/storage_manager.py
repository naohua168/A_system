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

    # ============================================================
    # 列名映射: DataFrame 列名 → MySQL 列名
    # 与 sync_to_mysql.py 中的 _map_* 函数保持同步
    # ============================================================
    COLUMN_MAP = {
        # stock 表（来自实时行情/股票基本信息 — 腾讯财经全市场扫描 22 字段）
        "stock": {
            "code": "stock_code",
            "name": "stock_name",
            "price": "current_price",
            "last_close": "yesterday_close",
            "open": "open_price",
            "high": "high_price",
            "low": "low_price",
            "change_amt": "change_amount",
            "change_pct": "change_percent",
            "amount_wan": "amount",
            "turnover_pct": "turnover_rate",
            "pe_ttm": "pe",
            "amplitude_pct": "amplitude",
            "mcap_yi": "total_market_cap",
            "float_mcap_yi": "float_market_cap",
            "pb": "pb",
            "limit_up": "limit_up",
            "limit_down": "limit_down",
            "vol_ratio": "vol_ratio",
            "pe_static": "pe_static",
            "source": "source",
        },
        # stock_daily 表（来自K线数据）
        "stock_daily": {
            "date": "trade_date",
            "stock_code": "stock_code",
            "open": "open_price",
            "close": "close_price",
            "high": "high_price",
            "low": "low_price",
            "volume": "volume",
            "amount": "amount",
            "pre_close": "pre_close",
            "change_pct": "change_percent",
            "turnover_pct": "turnover_rate",
        },
        # signal_hot_reason（同花顺热点）
        "signal_hot_reason": {
            "代码": "stock_code",
            "名称": "stock_name",
            "题材归因": "reason",
            "涨幅%": "change_pct",
            "换手率%": "turnover_pct",
            "fetch_date": "trade_date",
        },
        # signal_northbound（北向资金 — 分钟级 262 时间点）
        "signal_northbound": {
            "time": "time",
            "hgt_yi": "hgt_yi",
            "sgt_yi": "sgt_yi",
        },
        # signal_daily_industry（行业对比）
        "signal_daily_industry": {
            "rank": "rank_num",
            "name": "industry_name",
            "change_pct": "change_pct",
            "turnover_yi": "turnover_yi",
            "leader": "leader",
        },
        # info_cls_news（财联社快讯）
        "info_cls_news": {
            "标题": "title",
            "内容": "content",
            "发布时间": "publish_time",
        },
        # info_global_news（全球财经资讯）
        "info_global_news": {
            "标题": "title",
            "发布时间": "publish_time",
            "摘要": "summary",
            "来源": "source",
        },
        # signal_dragon_tiger_detail（龙虎榜明细）
        "signal_dragon_tiger_detail": {
            "code": "stock_code",
            "name": "stock_name",
            "stock_code": "stock_code",
            "stock_name": "stock_name",
            "reason": "reason",
            "close": "close",
            "change_pct": "change_pct",
            "net_buy_wan": "net_buy_wan",
            "buy_wan": "buy_wan",
            "sell_wan": "sell_wan",
            "turnover_pct": "turnover_pct",
            "trade_date": "trade_date",
        },
        # info_research_report（研报 — 东财 reportapi）
        "info_research_report": {
            "stock_code": "stock_code",
            "stock_name": "stock_name",
            "title": "title",
            "org_name": "org_name",
            "rating": "rating",
            "publish_date": "publish_date",
            "predict_eps_this_year": "eps_this_year",   # InformationCollector 返回的字段名
            "predict_eps_next_year": "eps_next_year",
            "page_url": "url",
        },
        # info_consensus_eps（一致预期 — 同花顺源 via akshare）
        "info_consensus_eps": {
            "code": "stock_code",           # 采集器添加的代码列
            "Stock_Code": "stock_code",     # 特定格式
            "年度": "year",
            "预测机构数": "num_analysts",
            "均值": "eps",                  # 取均值作为一致预期
            "平均": "eps",
        },
        # info_stock_news（个股新闻 — akshare 东财源）
        "info_stock_news": {
            "code": "stock_code",           # 采集器添加的代码列
            "新闻标题": "title",             # akshare 列名
            "新闻内容": "content_summary",
            "content": "content_summary",
            "新闻链接": "url",
            "发布时间": "publish_time",
            "datetime": "publish_time",
            "文章来源": "source",           # 新闻来源
        },
        # signal_concept_block（概念板块归属 — 百度源）
        "signal_concept_block": {
            "stock_code": "stock_code",
            "block_type": "block_type",
            "block_name": "block_name",
            "change_pct": "change_pct",
        },
        # signal_fund_flow（个股资金流向 — 百度/东财源）
        # DataFrame 列名来自 BaiduCollector._fetch_fund_flow_push2:
        #   date, close, ratio, superNetIn, largeNetIn, mediumNetIn, littleNetIn, mainIn
        # 也兼容 snake_case 格式的列名
        "signal_fund_flow": {
            "stock_code": "stock_code",
            # camelCase (push2 返回格式)
            "date": "trade_date",
            "ratio": "change_pct",
            "superNetIn": "super_net_in",
            "largeNetIn": "large_net_in",
            "mediumNetIn": "medium_net_in",
            "littleNetIn": "little_net_in",
            "mainIn": "main_in",
            # snake_case (其他源兼容)
            "trade_date": "trade_date",
            "change_pct": "change_pct",
            "super_net_in": "super_net_in",
            "large_net_in": "large_net_in",
            "medium_net_in": "medium_net_in",
            "little_net_in": "little_net_in",
            "main_in": "main_in",
            # 通用
            "close": "close",
        },
        # signal_lockup_detail（限售解禁明细 — akshare源）
        "signal_lockup_detail": {
            "stock_code": "stock_code",
            "lockup_date": "lockup_date",
            "lockup_type": "lockup_type",
            "shares": "shares",
            "float_ratio": "float_ratio",
            "type_tag": "type_tag",
        },
        # signal_dragon_tiger_detail（龙虎榜明细 — akshare源，已定义）

        # fund_holding（基金持仓 — akshare/东财源）
        "fund_holding": {
            "code": "fund_code",              # 采集器添加的代码列
            "stock_code": "stock_code",       # 英文列名（fetch_fund_holdings返回）
            "stock_name": "stock_name",
            "ratio": "ratio",
            "rank_num": "rank_num",
            # akshare 中文列名（兼容）
            "基金代码": "fund_code",
            "股票代码": "stock_code",
            "股票名称": "stock_name",
            "占净值比例": "ratio",
            "占净值比例(%)": "ratio",
            "持仓排名": "rank_num",
            "报告期": "report_date",
        },
    }

    # ============================================================
    # 值转换规则: {表名: {MySQL列名: (转换函数, 原DataFrame列名)}}
    # 在列名映射后、INSERT 前执行
    # ============================================================
    VALUE_TRANSFORM = {
        "stock": {
            "total_market_cap": (lambda v: v * 1e8 if v is not None else None, "mcap_yi"),
            "float_market_cap": (lambda v: v * 1e8 if v is not None else None, "float_mcap_yi"),
        },
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._conn = None
        self._connected = False

    def _get_connection(self):
        """获取 MySQL 连接（支持 Docker 多端口自动探测）"""
        if self._conn is not None:
            try:
                self._conn.ping(reconnect=True)
                return self._conn
            except Exception:
                self._conn = None

        import pymysql
        import os

        # 尝试多个连接候选（自动适配 Docker 内/外场景）
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "hadoop123")
        database = os.getenv("MYSQL_DB", "stock_analysis")
        port = int(os.getenv("MYSQL_PORT", "3306"))

        candidates = [
            {"host": os.getenv("MYSQL_HOST", "localhost"), "port": port},
            {"host": "localhost", "port": 3307},      # Docker dev: .env.dev 映射 3307
            {"host": "localhost", "port": 3306},      # 默认/本地
            {"host": "host.docker.internal", "port": 3306},  # 容器内连宿主机
            {"host": "mysql", "port": 3306},          # Docker 内网服务名
        ]

        last_error = None
        for cfg in candidates:
            try:
                self._conn = pymysql.connect(
                    host=cfg["host"],
                    port=cfg["port"],
                    user=user,
                    password=password,
                    database=database,
                    charset="utf8mb4",
                    connect_timeout=5,
                    read_timeout=10,
                    write_timeout=10,
                )
                self._connected = True
                logger.info("[MySQL] 连接成功: %s:%d", cfg["host"], cfg["port"])
                return self._conn
            except Exception as e:
                last_error = e
                continue

        logger.warning("[MySQL] 所有候选地址均连接失败: %s", last_error)
        raise ConnectionError(f"MySQL 连接失败: {last_error}")

    def close(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ============================================================
    # 缺失列自动填充规则: {表名: {列名: 填充值}}，在列名映射后执行
    # ============================================================
    FILL_COLUMNS = {
        "signal_northbound": {
            "trade_date": lambda: pd.Timestamp.now().strftime("%Y-%m-%d"),
        },
        "signal_hot_reason": {
            "trade_date": lambda: pd.Timestamp.now().strftime("%Y-%m-%d"),
        },
        "signal_daily_industry": {
            "trade_date": lambda: pd.Timestamp.now().strftime("%Y-%m-%d"),
        },
        "info_consensus_eps": {
            "stock_code": lambda: "",  # 待管道自动注入
        },
    }

    # ============================================================
    # 数据校验规则
    # ============================================================
    VALIDATION_RULES = {
        "stock": {
            "columns": ["stock_code", "stock_name"],
            "min_rows": 1,
            "require_non_null": ["stock_code"],
            "condition": lambda df: df["stock_code"].str.len() >= 6 if "stock_code" in df.columns else True,
        },
        "stock_daily": {
            "columns": ["stock_code", "trade_date", "close_price"],
            "min_rows": 1,
            "require_non_null": ["stock_code", "trade_date"],
        },
    }

    def _validate_data(self, table: str, df: pd.DataFrame) -> int:
        """校验数据合法性，返回通过校验的行数"""
        rules = self.VALIDATION_RULES.get(table)
        if not rules:
            return len(df)

        before = len(df)
        # 必填列非空检查
        for col in rules.get("require_non_null", []):
            if col in df.columns:
                df.dropna(subset=[col], inplace=True)

        # 自定义条件
        cond = rules.get("condition")
        if cond:
            try:
                valid_mask = cond(df)
                if isinstance(valid_mask, pd.Series):
                    df.drop(df[~valid_mask].index, inplace=True)
            except Exception:
                pass

        # 最小行数
        if len(df) < rules.get("min_rows", 1):
            logger.warning("[MySQL] %s 校验后无有效数据 (%d→0)", table, before)
            df.drop(df.index, inplace=True)

        dropped = before - len(df)
        if dropped:
            logger.info("[MySQL] %s 校验过滤: %d 行无效数据", table, dropped)
        return len(df)

    def write(self, table: str, df: pd.DataFrame,
              mode: str = "append") -> Tuple[int, int]:
        if df.empty:
            return (0, 0)

        # ----- 列名映射: DataFrame列 → MySQL列 -----
        mapping = self.COLUMN_MAP.get(table, {})
        if mapping:
            rename_map = {k: v for k, v in mapping.items() if k in df.columns}
            keep_cols = list(rename_map.keys())
            df = df[keep_cols].rename(columns=rename_map)

            # ----- 填充缺失的必填列 -----
            fill_rules = self.FILL_COLUMNS.get(table, {})
            for col, value_fn in fill_rules.items():
                if col not in df.columns:
                    df[col] = value_fn()

            # ----- 值转换（如 mcap_yi 亿→元）-----
            transform_rules = self.VALUE_TRANSFORM.get(table, {})
            for mysql_col, (transform_fn, df_col) in transform_rules.items():
                if mysql_col in df.columns:
                    df[mysql_col] = df[mysql_col].apply(transform_fn)

            if df.empty:
                logger.warning("[MySQL] %s 映射后无有效列", table)
                return (0, 0)

        conn = self._get_connection()
        cursor = conn.cursor()
        total_rows = len(df)
        inserted = 0
        batch_size = MYSQL_SYNC.get("batch_size", 200)

        try:
            # ----- 写入前数据校验（防止种子/无效数据入库）-----
            validated = self._validate_data(table, df)
            if validated < len(df):
                logger.info("[MySQL] %s 数据校验: %d/%d 行通过", table, validated, len(df))

            # 将 NaN/NaT 替换为 None（MySQL 的 NULL），否则 executemany 报错
            df = df.where(pd.notnull(df), None)

            placeholders = ", ".join(["%s"] * len(df.columns))
            cols = ", ".join(df.columns)
            sql = f"REPLACE INTO {table} ({cols}) VALUES ({placeholders})"

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
