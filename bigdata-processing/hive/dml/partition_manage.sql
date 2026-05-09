-- ============================================================
-- Hive 分区管理脚本
-- 包括: 新增分区、删除分区、查看分区、合并小文件
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 查看所有分区
-- ============================================================
SHOW PARTITIONS stock_daily;

-- ============================================================
-- 2. 手动新增分区（当直接往 HDFS 拷贝文件时使用）
-- ============================================================
ALTER TABLE stock_daily ADD IF NOT EXISTS
PARTITION (stock_code='000001', year=2026, month=5)
LOCATION '/user/hadoop/stock_data/daily/stock_code=000001/year=2026/month=5';

ALTER TABLE stock_daily ADD IF NOT EXISTS
PARTITION (stock_code='600519', year=2026, month=5)
LOCATION '/user/hadoop/stock_data/daily/stock_code=600519/year=2026/month=5';

-- ============================================================
-- 3. 删除指定分区
-- ============================================================
-- ALTER TABLE stock_daily DROP IF EXISTS
-- PARTITION (stock_code='000001', year=2026, month=4);

-- ============================================================
-- 4. 动态分区配置（执行 INSERT 前设置）
-- ============================================================
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;
SET hive.exec.max.dynamic.partitions = 5000;
SET hive.exec.max.dynamic.partitions.pernode = 1000;
SET hive.exec.max.created.files = 100000;

-- ============================================================
-- 5. 分区数据统计刷新（当 HDFS 文件有变动时）
-- ============================================================
ANALYZE TABLE stock_daily PARTITION(stock_code='000001', year=2026, month=5)
COMPUTE STATISTICS;

-- 全表统计（耗时较长，建议定期执行）
-- ANALYZE TABLE stock_daily COMPUTE STATISTICS;

-- ============================================================
-- 6. 修复所有分区（常用命令）
-- ============================================================
-- MSCK REPAIR TABLE stock_daily;
