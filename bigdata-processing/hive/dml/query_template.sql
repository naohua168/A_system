-- ============================================================
-- Hive 查询模板 — 验证数据通道 && 日常分析
-- 执行: beeline -u jdbc:hive2://localhost:10000 -f query_template.sql
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1️⃣  数据通道验证 — 确认数据已成功加载
-- ============================================================
SELECT '====== 数据通道验证 ======';

SELECT 'stock_basic 记录数:', COUNT(*) FROM stock_basic;
SELECT 'stock_daily 记录数:', COUNT(*) FROM stock_daily;
SELECT 'fund_nav 记录数:', COUNT(*) FROM fund_nav;

-- 查看有哪些股票代码
SELECT DISTINCT stock_code FROM stock_daily LIMIT 20;

-- 查看有哪些分区
SHOW PARTITIONS stock_daily;

-- ============================================================
-- 2️⃣  单只股票日K线数据
-- ============================================================
SELECT '====== 平安银行 (000001) 最近20个交易日 ======';

SELECT
    trade_date,
    open_price,
    close_price,
    high_price,
    low_price,
    volume,
    change_pct
FROM stock_daily
WHERE stock_code = '000001'
ORDER BY trade_date DESC
LIMIT 20;

-- ============================================================
-- 3️⃣  某日涨跌幅排名
-- ============================================================
SELECT '====== 指定日期涨跌幅排名 Top20 ======';

SELECT
    s.stock_code,
    b.name,
    s.trade_date,
    s.close_price,
    s.change_pct,
    s.volume
FROM stock_daily s
JOIN stock_basic b ON s.stock_code = b.code
WHERE s.trade_date = '2026-05-08'
ORDER BY ABS(s.change_pct) DESC
LIMIT 20;

-- ============================================================
-- 4️⃣  行业平均涨跌幅
-- ============================================================
SELECT '====== 行业平均涨跌幅 ======';

SELECT
    b.industry,
    COUNT(*) AS stock_count,
    ROUND(AVG(s.change_pct), 2) AS avg_change_pct,
    ROUND(MAX(s.change_pct), 2) AS max_change,
    ROUND(MIN(s.change_pct), 2) AS min_change
FROM stock_daily s
JOIN stock_basic b ON s.stock_code = b.code
WHERE s.trade_date = '2026-05-08'
  AND b.industry IS NOT NULL
GROUP BY b.industry
ORDER BY avg_change_pct DESC;

-- ============================================================
-- 5️⃣  月度均价统计
-- ============================================================
SELECT '====== 000001 月度均价统计 ======';

SELECT
    stock_code,
    year,
    month,
    ROUND(AVG(close_price), 2) AS avg_close,
    ROUND(MIN(low_price), 2) AS min_low,
    ROUND(MAX(high_price), 2) AS max_high,
    ROUND(SUM(volume), 0) AS total_volume
FROM stock_daily
WHERE stock_code = '000001'
GROUP BY stock_code, year, month
ORDER BY year, month;

-- ============================================================
-- 6️⃣  基金净值走势
-- ============================================================
SELECT '====== 基金净值最近30天 ======';

SELECT
    nav_date,
    fund_code,
    nav,
    accum_nav,
    daily_change
FROM fund_nav
WHERE fund_code = '000001'
ORDER BY nav_date DESC
LIMIT 30;
