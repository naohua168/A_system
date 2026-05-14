-- ===========================================
-- Hive DDL: 信号层表（a-stock-data 新增）
-- 题材归因 / 北向资金 / 行业对比 / 个股综合信号
-- ===========================================

-- 1. 题材归因表
-- HDFS路径: /user/hadoop/stock_data/signals/hot_reason/
CREATE EXTERNAL TABLE IF NOT EXISTS stock_analysis.signal_hot_reason (
    code        STRING COMMENT '股票代码',
    name        STRING COMMENT '股票名称',
    reason      STRING COMMENT '题材归因标签',
    close       DOUBLE COMMENT '收盘价',
    zhangfu     DOUBLE COMMENT '涨幅%',
    huanshou    DOUBLE COMMENT '换手率%',
    chengjiaoe  DOUBLE COMMENT '成交额',
    ddejingliang DOUBLE COMMENT '大单净量',
    market      STRING COMMENT '市场',
    fetch_date  STRING COMMENT '采集日期'
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar' = '"',
    'skip.header.line.count' = '1'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/signals/hot_reason/';

-- 2. 北向资金表
-- HDFS路径: /user/hadoop/stock_data/signals/northbound/
CREATE EXTERNAL TABLE IF NOT EXISTS stock_analysis.signal_northbound (
    time      STRING COMMENT '时间',
    hgt_yi    DOUBLE COMMENT '沪股通累计净买入(亿)',
    sgt_yi    DOUBLE COMMENT '深股通累计净买入(亿)'
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar' = '"',
    'skip.header.line.count' = '1'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/signals/northbound/';

-- 3. 行业对比表
-- HDFS路径: /user/hadoop/stock_data/signals/industry/
CREATE EXTERNAL TABLE IF NOT EXISTS stock_analysis.signal_industry (
    rank         INT COMMENT '排名',
    name         STRING COMMENT '行业名称',
    change_pct   DOUBLE COMMENT '涨跌幅%',
    turnover_yi  DOUBLE COMMENT '总成交额(亿)',
    net_inflow_yi DOUBLE COMMENT '净流入(亿)',
    up_count     INT COMMENT '上涨家数',
    down_count   INT COMMENT '下跌家数',
    leader       STRING COMMENT '领涨股',
    fetch_date   STRING COMMENT '采集日期'
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar' = '"',
    'skip.header.line.count' = '1'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/signals/industry/';

-- 4. 个股综合信号表
-- HDFS路径: /user/hadoop/stock_data/signals/stock/
CREATE EXTERNAL TABLE IF NOT EXISTS stock_analysis.signal_stock (
    stock_code      STRING COMMENT '股票代码',
    concept_tags    STRING COMMENT '概念板块标签',
    fund_flow_main  DOUBLE COMMENT '主力资金净流入(万)',
    dragon_tiger_count INT COMMENT '近30日龙虎榜次数',
    lockup_upcoming   INT COMMENT '未来90天解禁批次',
    fetch_date      STRING COMMENT '采集日期'
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar' = '"',
    'skip.header.line.count' = '1'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/signals/stock/';
