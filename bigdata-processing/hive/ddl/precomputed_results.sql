-- ============================================================
-- Hive DDL: 预计算结果表
-- 将高频分析查询的结果物化为持久表，提升查询性能
-- 通过批处理管道定期刷新
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 股票年收益率预计算表
-- 存储每只股票每年的收益率及全市场排名
-- 刷新频率: 每日批处理 (增量)
-- ============================================================
DROP TABLE IF EXISTS precomputed_yearly_return;

CREATE TABLE precomputed_yearly_return (
    stock_code   STRING  COMMENT '股票代码',
    trade_year   INT     COMMENT '交易年份',
    yearly_return DOUBLE COMMENT '年收益率 (%)',
    rank         INT     COMMENT '当年全市场排名 (1=最高)',
    updated_at   STRING  COMMENT '数据刷新时间'
)
COMMENT '股票年收益率预计算结果表 - Parquet列式存储'
STORED AS PARQUET
LOCATION '/user/hadoop/stock_data/precomputed/yearly_return/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- ============================================================
-- 2. 移动均线信号预计算表
-- 存储每只股票每日的 MA5/MA10/MA20/MA60 及交叉信号
-- 刷新频率: 每日批处理 (增量)
-- ============================================================
DROP TABLE IF EXISTS precomputed_ma_signal;

CREATE TABLE precomputed_ma_signal (
    stock_code       STRING  COMMENT '股票代码',
    trade_date       STRING  COMMENT '交易日期 YYYY-MM-DD',
    ma5              DOUBLE  COMMENT '5日均线',
    ma10             DOUBLE  COMMENT '10日均线',
    ma20             DOUBLE  COMMENT '20日均线',
    ma60             DOUBLE  COMMENT '60日均线',
    crossover_signal STRING  COMMENT '金叉/死叉信号 (golden/death/none)',
    updated_at       STRING  COMMENT '数据刷新时间'
)
COMMENT '移动均线信号预计算结果表'
STORED AS PARQUET
LOCATION '/user/hadoop/stock_data/precomputed/ma_signal/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

-- ============================================================
-- 3. 股票相关性预计算表
-- 存储股票对之间的价格相关系数 (Pearson)
-- 刷新频率: 全量每日
-- ============================================================
DROP TABLE IF EXISTS precomputed_correlation;

CREATE TABLE precomputed_correlation (
    stock_code_a STRING  COMMENT '股票A代码',
    stock_code_b STRING  COMMENT '股票B代码',
    industry     STRING  COMMENT '所属行业 (若同行业)',
    correlation  DOUBLE  COMMENT 'Pearson相关系数 (-1 ~ 1)',
    updated_at   STRING  COMMENT '数据刷新时间'
)
COMMENT '股票价格相关系数预计算结果表'
STORED AS PARQUET
LOCATION '/user/hadoop/stock_data/precomputed/correlation/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
