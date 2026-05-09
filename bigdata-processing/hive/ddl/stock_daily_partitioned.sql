-- ============================================================
-- 日K线数据分区表
-- 按 股票代码 + 年份 + 月份 三级分区
-- 存储格式: PARQUET (列式存储，查询性能优于 TEXTFILE)
-- 数据路径: HDFS /user/hadoop/stock_data/daily/
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 日K线数据表（分区表）
-- 原始数据 → 清洗后写入 Parquet 格式
-- ============================================================
DROP TABLE IF EXISTS stock_daily;

CREATE EXTERNAL TABLE stock_daily (
    trade_date  STRING  COMMENT '交易日期 YYYY-MM-DD',
    open_price  DOUBLE  COMMENT '开盘价',
    high_price  DOUBLE  COMMENT '最高价',
    low_price   DOUBLE  COMMENT '最低价',
    close_price DOUBLE  COMMENT '收盘价',
    pre_close   DOUBLE  COMMENT '昨收价',
    volume      BIGINT  COMMENT '成交量 (股)',
    amount      DOUBLE  COMMENT '成交额 (元)',
    change_pct  DOUBLE  COMMENT '涨跌幅 (%)',
    turnover    DOUBLE  COMMENT '换手率 (%)',
    amplitude   DOUBLE  COMMENT '振幅 (%)'
)
COMMENT '股票日K线数据分区表 - Parquet列式存储'
PARTITIONED BY (stock_code STRING, year INT, month INT)
STORED AS PARQUET
LOCATION '/user/hadoop/stock_data/daily/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- ============================================================
-- 2. 分区维护 — 修复分区元数据
-- 当数据文件通过 HDFS put 上传后，执行 MSCK 修复
-- ============================================================
-- MSCK REPAIR TABLE stock_daily;

-- ============================================================
-- 3. 日K线临时表（用于从原始 CSV 加载到分区表）
-- ============================================================
DROP TABLE IF EXISTS stock_daily_staging;

CREATE EXTERNAL TABLE stock_daily_staging (
    trade_date  STRING  COMMENT '交易日期',
    open_price  DOUBLE  COMMENT '开盘价',
    high_price  DOUBLE  COMMENT '最高价',
    low_price   DOUBLE  COMMENT '最低价',
    close_price DOUBLE  COMMENT '收盘价',
    volume      BIGINT  COMMENT '成交量',
    amount      DOUBLE  COMMENT '成交额',
    change_pct  DOUBLE  COMMENT '涨跌幅',
    turnover    DOUBLE  COMMENT '换手率',
    stock_code  STRING  COMMENT '股票代码'
)
COMMENT '日K线数据原始加载临时表 - TEXTFILE'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/staging/daily/'
TBLPROPERTIES ('skip.header.line.count' = '1');
