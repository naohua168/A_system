-- ============================================================
-- Hive 分析查询 — 涨跌幅统计
-- 基于 stock_daily 分区表 (Parquet)
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 每日涨跌幅排名 （涨幅榜 + 跌幅榜）
-- ============================================================
SELECT '1️⃣  2026-05-08 涨幅榜 Top10';

SELECT
    d.stock_code,
    b.name,
    d.close_price,
    d.change_pct,
    d.volume
FROM stock_daily d
JOIN stock_basic b ON d.stock_code = b.code
WHERE d.trade_date = '2026-05-08'
  AND d.change_pct IS NOT NULL
ORDER BY d.change_pct DESC
LIMIT 10;

SELECT '   同日 跌幅榜 Top10';

SELECT
    d.stock_code,
    b.name,
    d.close_price,
    d.change_pct,
    d.volume
FROM stock_daily d
JOIN stock_basic b ON d.stock_code = b.code
WHERE d.trade_date = '2026-05-08'
  AND d.change_pct IS NOT NULL
ORDER BY d.change_pct ASC
LIMIT 10;

-- ============================================================
-- 2. 周/月/年涨跌幅排名
-- ============================================================
SELECT '2️⃣  2026年5月 累积涨幅 Top20';

SELECT
    stock_code,
    ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS month_return,
    ROUND(MIN(close_price), 2) AS min_price,
    ROUND(MAX(close_price), 2) AS max_price,
    COUNT(*) AS trade_days
FROM stock_daily
WHERE year = 2026 AND month = 5
GROUP BY stock_code
HAVING COUNT(*) >= 10
ORDER BY month_return DESC
LIMIT 20;

SELECT '   月累积跌幅 Top20';

SELECT
    stock_code,
    ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS month_return,
    ROUND(MIN(close_price), 2) AS min_price,
    ROUND(MAX(close_price), 2) AS max_price,
    COUNT(*) AS trade_days
FROM stock_daily
WHERE year = 2026 AND month = 5
GROUP BY stock_code
HAVING COUNT(*) >= 10
ORDER BY month_return ASC
LIMIT 20;

-- ============================================================
-- 3. 行业涨跌榜
-- ============================================================
SELECT '3️⃣  2026-05-08 行业涨跌幅排行';

SELECT
    b.industry,
    COUNT(*) AS stock_count,
    ROUND(AVG(d.change_pct), 2) AS avg_change_pct,
    ROUND(SUM(CASE WHEN d.change_pct > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS up_ratio,
    ROUND(SUM(CASE WHEN d.change_pct > 9.5 THEN 1 ELSE 0 END), 0) AS limit_up_cnt,
    ROUND(SUM(CASE WHEN d.change_pct < -9.5 THEN 1 ELSE 0 END), 0) AS limit_down_cnt
FROM stock_daily d
JOIN stock_basic b ON d.stock_code = b.code
WHERE d.trade_date = '2026-05-08'
  AND b.industry IS NOT NULL
  AND d.change_pct IS NOT NULL
GROUP BY b.industry
ORDER BY avg_change_pct DESC;

-- ============================================================
-- 4. 连续涨跌天数统计（涨跌停信号）
-- ============================================================
SELECT '4️⃣  连续上涨天数最多的股票';

-- 使用 Hive 的 LAG 窗口函数计算连续涨跌
-- 需要 Hive 2.1+ 支持
SELECT
    stock_code,
    trade_date,
    change_pct,
    CASE
        WHEN change_pct > 0 THEN 'UP'
        WHEN change_pct < 0 THEN 'DOWN'
        ELSE 'FLAT'
    END AS direction
FROM stock_daily
WHERE stock_code IN ('000001', '600519', '300750')
  AND trade_date >= DATE_SUB(CURRENT_DATE, 60)
ORDER BY stock_code, trade_date;

-- ============================================================
-- 5. 振幅排行（日内波动最大）
-- ============================================================
SELECT '5️⃣  2026-05-08 日内振幅最大 Top20';

SELECT
    d.stock_code,
    b.name,
    ROUND(d.high_price - d.low_price, 2) AS day_range,
    ROUND((d.high_price - d.low_price) / d.pre_close * 100, 2) AS amplitude_pct,
    d.high_price,
    d.low_price,
    d.close_price
FROM stock_daily d
JOIN stock_basic b ON d.stock_code = b.code
WHERE d.trade_date = '2026-05-08'
  AND d.pre_close > 0
ORDER BY amplitude_pct DESC
LIMIT 20;
