-- ============================================================
-- Hive 数据库: stock_analysis
-- 股票基本信息外部表
-- 数据来源: data-collector 采集的 CSV 文件
-- 存储格式: TEXTFILE (与 Python 采集输出兼容)
-- 数据路径: HDFS /user/hadoop/stock_data/basic/
-- ============================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS stock_analysis
COMMENT '基金股票智能分析系统 - Hive 数据仓库'
LOCATION '/user/hive/warehouse/stock_analysis.db';

USE stock_analysis;

-- ============================================================
-- 1. 股票基本信息外部表
-- 关联采集到的 stock_basic_*.csv 文件
-- ============================================================
DROP TABLE IF EXISTS stock_basic;

CREATE EXTERNAL TABLE stock_basic (
    code        STRING  COMMENT '股票代码',
    name        STRING  COMMENT '股票名称',
    market      STRING  COMMENT '所属市场 (SH/SZ/BJ)',
    industry    STRING  COMMENT '所属行业',
    listing_date STRING COMMENT '上市日期 YYYY-MM-DD',
    total_market_cap DOUBLE COMMENT '总市值 (元)',
    float_market_cap  DOUBLE COMMENT '流通市值 (元)',
    pe          DOUBLE  COMMENT '市盈率(动态)',
    pb          DOUBLE  COMMENT '市净率',
    source      STRING  COMMENT '数据来源 (eastmoney/baostock)'
)
COMMENT '股票基本信息表 - 外部表关联HDFS CSV'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/basic/'
TBLPROPERTIES ('skip.header.line.count' = '1');

-- ============================================================
-- 2. 股票行业编码维度表（可选，辅助分析）
-- ============================================================
DROP TABLE IF EXISTS dim_industry;

CREATE EXTERNAL TABLE dim_industry (
    industry_code   STRING COMMENT '行业代码',
    industry_name   STRING COMMENT '行业名称',
    board           STRING COMMENT '所属板块'
)
COMMENT '行业编码维度表'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/dim/industry/'
TBLPROPERTIES ('skip.header.line.count' = '1');
