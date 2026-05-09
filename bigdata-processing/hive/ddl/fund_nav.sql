-- ============================================================
-- 基金相关 Hive 表
-- 涵盖基金基本信息、净值走势、持仓信息
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 基金净值外部表
-- 数据来源: data-collector 采集的 fund_nav_*.csv
-- ============================================================
DROP TABLE IF EXISTS fund_nav;

CREATE EXTERNAL TABLE fund_nav (
    nav_date    STRING  COMMENT '净值日期 YYYY-MM-DD',
    nav         DOUBLE  COMMENT '单位净值',
    accum_nav   DOUBLE  COMMENT '累计净值',
    daily_change DOUBLE COMMENT '日涨跌幅 (%)',
    fund_code   STRING  COMMENT '基金代码',
    source      STRING  COMMENT '数据来源'
)
COMMENT '基金净值数据表 - 外部表关联HDFS CSV'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/nav/'
TBLPROPERTIES ('skip.header.line.count' = '1');

-- ============================================================
-- 2. 基金基本信息表
-- ============================================================
DROP TABLE IF EXISTS fund_basic;

CREATE EXTERNAL TABLE fund_basic (
    fund_code   STRING  COMMENT '基金代码',
    fund_name   STRING  COMMENT '基金名称',
    fund_type   STRING  COMMENT '基金类型 (股票型/混合型/债券型等)',
    fund_company STRING COMMENT '基金公司',
    establish_date STRING COMMENT '成立日期',
    fund_size   DOUBLE  COMMENT '基金规模 (亿元)',
    manager     STRING  COMMENT '基金经理',
    source      STRING  COMMENT '数据来源'
)
COMMENT '基金基本信息表'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/basic/'
TBLPROPERTIES ('skip.header.line.count' = '1');
