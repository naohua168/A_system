-- ============================================================
-- Hive ORC 格式优化表 — 替代 TEXTFILE 获得 10x+ 查询性能
-- ============================================================
-- ORC (Optimized Row Columnar) 优势:
--   - 列式存储: 只读取查询需要的列，减少 I/O 达 80%
--   - 内置索引: min/max 索引 + Bloom Filter，加速 WHERE 过滤
--   - 压缩率高: ZLIB 压缩比 TEXTFILE 节省 75% 空间
--   - 谓词下推: WHERE 条件下推到存储层执行
--
-- 迁移方案:
--   1. 先用 CREATE TABLE LIKE + STORED AS ORC 创建骨架
--   2. 用 INSERT OVERWRITE 从 TEXTFILE 表转换数据
--   3. 重命名切换
-- ============================================================

USE stock_analysis;


-- ============================================================
-- 1. stock_daily ORC 优化版（带分区和排序）
-- ============================================================
DROP TABLE IF EXISTS stock_daily_orc;

CREATE TABLE stock_daily_orc (
    stock_code  STRING  COMMENT '股票代码',
    trade_date  STRING  COMMENT '交易日',
    open_price  DOUBLE  COMMENT '开盘价',
    high_price  DOUBLE  COMMENT '最高价',
    low_price   DOUBLE  COMMENT '最低价',
    close_price DOUBLE  COMMENT '收盘价',
    change_pct  DOUBLE  COMMENT '涨跌幅(%)',
    volume      BIGINT  COMMENT '成交量(股)',
    amount      DOUBLE  COMMENT '成交额(元)',
    amplitude   DOUBLE  COMMENT '振幅(%)',
    source      STRING  COMMENT '数据来源'
)
COMMENT '日K线数据 — ORC 格式优化版'
PARTITIONED BY (year INT, month INT)
CLUSTERED BY (stock_code) INTO 16 BUCKETS  -- 按股票代码分桶，加速 JOIN
STORED AS ORC
TBLPROPERTIES (
    'orc.compress' = 'ZLIB',                     -- ORC 默认 ZLIB 压缩
    'orc.compress.size' = '262144',               -- 压缩块大小 256KB
    'orc.stripe.size' = '268435456',              -- Stripe 大小 256MB
    'orc.row.index.stride' = '10000',             -- 行索引步长
    'orc.create.index' = 'true',                  -- 创建索引
    'orc.bloom.filter.columns' = 'stock_code',    -- 对股票代码建 Bloom Filter
    'orc.bloom.filter.fpp' = '0.05',              -- Bloom Filter 假阳性率
    'orc.bloom.filter.write.version' = '2'
);


-- ============================================================
-- 2. stock_basic ORC 优化版
-- ============================================================
DROP TABLE IF EXISTS stock_basic_orc;

CREATE TABLE stock_basic_orc (
    code             STRING  COMMENT '股票代码',
    name             STRING  COMMENT '股票名称',
    market           STRING  COMMENT '所属市场',
    industry         STRING  COMMENT '所属行业',
    listing_date     STRING  COMMENT '上市日期',
    total_market_cap DOUBLE  COMMENT '总市值',
    float_market_cap DOUBLE  COMMENT '流通市值',
    pe               DOUBLE  COMMENT '市盈率',
    pb               DOUBLE  COMMENT '市净率',
    roe              DOUBLE  COMMENT '净资产收益率(%)',
    market_cap       DOUBLE  COMMENT '总市值(元)',
    source           STRING  COMMENT '数据来源'
)
COMMENT '股票基本信息 — ORC 格式优化版'
STORED AS ORC
TBLPROPERTIES (
    'orc.compress' = 'ZLIB',
    'orc.bloom.filter.columns' = 'code,industry',
    'orc.bloom.filter.fpp' = '0.05'
);


-- ============================================================
-- 3. 数据迁移 SQL（从 TEXTFILE 表导入 ORC 表）
-- ============================================================
-- 全量迁移:
-- INSERT OVERWRITE TABLE stock_daily_orc PARTITION (year, month)
-- SELECT stock_code, trade_date, open_price, high_price, low_price,
--        close_price, change_pct, volume, amount, amplitude, source,
--        CAST(SUBSTR(trade_date, 1, 4) AS INT) AS year,
--        CAST(SUBSTR(trade_date, 6, 2) AS INT) AS month
-- FROM stock_daily;
--
-- INSERT OVERWRITE TABLE stock_basic_orc
-- SELECT * FROM stock_basic;
--
-- 迁移后切换（可选）:
-- ALTER TABLE stock_daily RENAME TO stock_daily_textfile;
-- ALTER TABLE stock_daily_orc RENAME TO stock_daily;
-- ============================================================


-- ============================================================
-- 4. ANALYZE TABLE 收集统计信息（优化查询计划）
-- ============================================================
-- 数据加载完成后执行:
-- ANALYZE TABLE stock_daily_orc COMPUTE STATISTICS;
-- ANALYZE TABLE stock_daily_orc COMPUTE STATISTICS FOR COLUMNS;
-- ANALYZE TABLE stock_basic_orc COMPUTE STATISTICS;
-- ============================================================


-- ============================================================
-- 5. 查询性能对比验证 SQL
-- ============================================================
-- TEXTFILE 版:
--   SELECT industry, AVG(change_pct) FROM stock_daily d
--   JOIN stock_basic b ON d.stock_code = b.code
--   WHERE d.trade_date = '2026-05-08' GROUP BY industry;
--
-- ORC 版（预期快 5~15 倍）:
--   SELECT industry, AVG(change_pct) FROM stock_daily_orc d
--   JOIN stock_basic_orc b ON d.stock_code = b.code
--   WHERE d.year = 2026 AND d.month = 5 AND d.trade_date = '2026-05-08'
--   GROUP BY industry;
-- ============================================================
