-- Hive 外部表 DDL：指向 HDFS 上的 CSV 数据
-- 所有表使用 OpenCSVSerde 解析 CSV，跳过表头行

--- 1. 股票基本信息 (from collect_full_market tencent_quote)
CREATE EXTERNAL TABLE IF NOT EXISTS stock_basic (
    stock_code STRING, stock_name STRING, pe_ttm DOUBLE,
    pb DOUBLE, mcap_yi DOUBLE, turnover_pct DOUBLE, source STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/basic'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 2. 北向资金
CREATE EXTERNAL TABLE IF NOT EXISTS signal_northbound (
    trade_date STRING, hgt_yi DOUBLE, sgt_yi DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/signals/northbound'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 3. 财联社快讯
CREATE EXTERNAL TABLE IF NOT EXISTS info_cls_news (
    title STRING, content STRING, datetime STRING, source STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/info/cls_news'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 4. 全球资讯
CREATE EXTERNAL TABLE IF NOT EXISTS info_global_news (
    title STRING, summary STRING, publish_time STRING, url STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/info/global_news'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 5. 基金净值
CREATE EXTERNAL TABLE IF NOT EXISTS fund_nav (
    fund_code STRING, nav_date STRING, nav DOUBLE, accumulated_nav DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/nav'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 6. 基金列表
CREATE EXTERNAL TABLE IF NOT EXISTS fund_list (
    fund_code STRING, scale DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/details'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 7. 基金基本信息
CREATE EXTERNAL TABLE IF NOT EXISTS fund_basic (
    fund_code STRING, fund_name STRING, fund_type STRING, company STRING, scale DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/basic'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 8. 题材热点
CREATE EXTERNAL TABLE IF NOT EXISTS signal_hot_reason (
    id STRING, name STRING, code STRING, reason STRING, trade_date STRING,
    close_price DOUBLE, change DOUBLE, change_pct DOUBLE, turnover_pct DOUBLE,
    amount DOUBLE, volume DOUBLE, big_net_pct DOUBLE, market STRING,
    source STRING, fetch_date STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/signals/hot_reason'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 9. 腾讯实时行情 (collect_full_market 采集)
CREATE EXTERNAL TABLE IF NOT EXISTS tencent_quote (
    stock_code STRING, stock_name STRING, price DOUBLE, pe_ttm DOUBLE,
    pb DOUBLE, mcap_yi DOUBLE, turnover_pct DOUBLE, change_pct DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/tencent_quote'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 10. 个股资金流向
CREATE EXTERNAL TABLE IF NOT EXISTS stock_fund_flow (
    stock_code STRING, trade_date STRING, main_net STRING, small_net STRING,
    mid_net STRING, large_net STRING, super_net STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund_flow'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 11. 龙虎榜
CREATE EXTERNAL TABLE IF NOT EXISTS dragon_tiger (
    trade_date STRING, stock_code STRING, stock_name STRING, reason STRING,
    net_buy_wan DOUBLE, buy_wan DOUBLE, sell_wan DOUBLE, change_pct DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/dragon_tiger'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 12. 行业对比
CREATE EXTERNAL TABLE IF NOT EXISTS industry_compare (
    industry STRING, code STRING, change_pct DOUBLE, up_count INT, down_count INT
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/industry_compare'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 13. 概念板块
CREATE EXTERNAL TABLE IF NOT EXISTS concept_blocks (
    stock_code STRING, block_name STRING, block_type STRING, change_pct STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/concept_blocks'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 14. 限售解禁
CREATE EXTERNAL TABLE IF NOT EXISTS stock_lockup (
    stock_code STRING, free_date STRING, lockup_type STRING, shares BIGINT, ratio DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/lockup'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 15. 个股新闻
CREATE EXTERNAL TABLE IF NOT EXISTS stock_news (
    stock_code STRING, title STRING, content STRING, publish_time STRING, source STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/stock_news'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 16. 巨潮公告
CREATE EXTERNAL TABLE IF NOT EXISTS stock_filings (
    stock_code STRING, title STRING, type STRING, publish_date STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/filings'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 17. 日K线数据
CREATE EXTERNAL TABLE IF NOT EXISTS stock_daily (
    stock_code STRING, trade_date STRING, open DOUBLE, high DOUBLE,
    low DOUBLE, close DOUBLE, volume BIGINT, amount DOUBLE, change_pct DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/daily'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 18. 腾讯指数行情 (collector 新增采集)
CREATE EXTERNAL TABLE IF NOT EXISTS tencent_index (
    index_code STRING, index_name STRING, price DOUBLE, change_pct DOUBLE,
    open DOUBLE, high DOUBLE, low DOUBLE, volume BIGINT, amount DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/index/quote'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 19. 指数日K线
CREATE EXTERNAL TABLE IF NOT EXISTS index_daily (
    index_code STRING, trade_date STRING, open DOUBLE, high DOUBLE,
    low DOUBLE, close DOUBLE, volume BIGINT, amount DOUBLE, change_pct DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/index/daily'
TBLPROPERTIES ('skip.header.line.count' = '1');

--- 20. stock_industry — 股票行业归属（JOIN用）
CREATE EXTERNAL TABLE IF NOT EXISTS stock_industry (
    stock_code STRING, industry STRING, industry_en STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/industry'
TBLPROPERTIES ('skip.header.line.count' = '1');

SHOW TABLES;
