-- Hive 外部表 DDL：指向 HDFS 上的 CSV 数据
-- 所有表使用 OpenCSVSerde 解析 CSV，跳过表头行

--- 1. 股票基本信息
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

--- 4. 基金净值
CREATE EXTERNAL TABLE IF NOT EXISTS fund_nav (
    fund_code STRING, nav_date STRING, nav DOUBLE, accumulated_nav DOUBLE
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/fund/nav'
TBLPROPERTIES ('skip.header.line.count' = '1');

SHOW TABLES;
SELECT 'stock_basic' AS tbl, COUNT(*) AS cnt FROM stock_basic
UNION ALL
SELECT 'signal_northbound', COUNT(*) FROM signal_northbound
UNION ALL
SELECT 'info_cls_news', COUNT(*) FROM info_cls_news
UNION ALL
SELECT 'fund_nav', COUNT(*) FROM fund_nav;
