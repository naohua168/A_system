-- ============================================================
-- Hive 数据加载脚本 (DML)
-- 将 HDFS 上的 CSV 数据加载到 Hive 表中
-- 执行顺序: 1→2→3→4
-- ============================================================

-- 1. 加载股票基本信息到外部表
-- 数据文件: stock_basic_*.csv → HDFS /user/hadoop/stock_data/basic/
-- 说明: 外部表只需将文件放到对应 HDFS 路径即可自动识别
-- 如果已有文件在 HDFS 路径，执行 MSCK 刷新
MSCK REPAIR TABLE stock_analysis.stock_basic;

-- 验证加载
SELECT COUNT(*) AS basic_count FROM stock_analysis.stock_basic;
SELECT * FROM stock_analysis.stock_basic LIMIT 10;

-- ============================================================
-- 2. 从原始 CSV 加载到分区表（临时表 → 最终表）
-- 使用 stock_daily_staging 临时表 + INSERT ... PARTITION
-- ============================================================

-- 2a. 将采集的 CSV 上传到 staging 路径
-- HDFS 命令示例:
--   hdfs dfs -put data/raw/kline_000001_daily_20260508.csv /user/hadoop/stock_data/staging/daily/

-- 2b. 修复 staging 表元数据
MSCK REPAIR TABLE stock_analysis.stock_daily_staging;

-- 2c. 从 staging 表动态插入到分区表
-- 注意: 需要先启用动态分区
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;
SET hive.exec.max.dynamic.partitions = 5000;

INSERT OVERWRITE TABLE stock_analysis.stock_daily
PARTITION (stock_code, year, month)
SELECT
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    amount,
    change_pct,
    turnover,
    NULL AS amplitude,        -- 振幅（如无数据）
    stock_code,
    CAST(SUBSTR(trade_date, 1, 4) AS INT) AS year,
    CAST(SUBSTR(trade_date, 6, 2) AS INT) AS month
FROM stock_analysis.stock_daily_staging
WHERE trade_date IS NOT NULL
  AND stock_code IS NOT NULL;

-- 2d. 验证分区加载
SHOW PARTITIONS stock_analysis.stock_daily;
SELECT stock_code, COUNT(*) AS cnt
FROM stock_analysis.stock_daily
GROUP BY stock_code;

-- ============================================================
-- 3. 加载基金净值数据
-- ============================================================
MSCK REPAIR TABLE stock_analysis.fund_nav;
SELECT COUNT(*) AS fund_nav_count FROM stock_analysis.fund_nav;
SELECT * FROM stock_analysis.fund_nav LIMIT 10;

-- ============================================================
-- 4. 一键全量刷新（当所有数据已上传到 HDFS 后执行）
-- ============================================================
-- MSCK REPAIR TABLE stock_analysis.stock_basic;
-- MSCK REPAIR TABLE stock_analysis.stock_daily_staging;
-- MSCK REPAIR TABLE stock_analysis.fund_nav;
-- MSCK REPAIR TABLE stock_analysis.fund_basic;
