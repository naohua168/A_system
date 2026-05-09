-- ============================================================
-- Hive 分析查询 — 日均价统计
-- 基于 stock_daily 分区表 (Parquet)
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 单只股票日均价统计（指定时间范围）
-- ============================================================
SELECT '1️⃣  平安银行 最近30日日均价';

SELECT
    stock_code,
    trade_date,
    ROUND((open_price + high_price + low_price + close_price) / 4, 2) AS avg_price,
    open_price,
    close_price,
    high_price,
    low_price,
    volume
FROM stock_daily
WHERE stock_code = '000001'
  AND trade_date >= DATE_SUB(CURRENT_DATE, 30)
ORDER BY trade_date DESC;

-- ============================================================
-- 2. 月均价统计（全市场）
-- ============================================================
SELECT '2️⃣  2026年5月 各股票月均价 Top20';

SELECT
    stock_code,
    ROUND(AVG(close_price), 2) AS month_avg_close,
    ROUND(MIN(low_price), 2) AS month_min_low,
    ROUND(MAX(high_price), 2) AS month_max_high,
    ROUND(AVG(volume), 0) AS avg_daily_volume,
    COUNT(*) AS trade_days
FROM stock_daily
WHERE year = 2026 AND month = 5
GROUP BY stock_code
ORDER BY month_avg_close DESC
LIMIT 20;

-- ============================================================
-- 3. 年同比均价对比（今年的月度均价 vs 去年同月）
-- ============================================================
SELECT '3️⃣  000001 月均价同比 (2026 vs 2025)';

SELECT
    a.month,
    a.avg_close AS avg_2026,
    b.avg_close AS avg_2025,
    ROUND((a.avg_close - b.avg_close) / b.avg_close * 100, 2) AS yoy_change_pct
FROM (
    SELECT month, ROUND(AVG(close_price), 2) AS avg_close
    FROM stock_daily
    WHERE stock_code = '000001' AND year = 2026
    GROUP BY month
) a
JOIN (
    SELECT month, ROUND(AVG(close_price), 2) AS avg_close
    FROM stock_daily
    WHERE stock_code = '000001' AND year = 2025
    GROUP BY month
) b ON a.month = b.month
ORDER BY a.month;

-- ============================================================
-- 4. 行业月均价排行
-- ============================================================
SELECT '4️⃣  2026年5月 行业均价排行';

SELECT
    b.industry,
    COUNT(DISTINCT d.stock_code) AS stock_count,
    ROUND(AVG(d.close_price), 2) AS industry_avg_price,
    ROUND(MAX(d.close_price), 2) AS industry_max,
    ROUND(MIN(d.close_price), 2) AS industry_min
FROM stock_daily d
JOIN stock_basic b ON d.stock_code = b.code
WHERE d.year = 2026 AND d.month = 5
  AND b.industry IS NOT NULL
GROUP BY b.industry
ORDER BY industry_avg_price DESC;

-- ============================================================
-- 5. 价格波动率统计（月内标准差/均值）
-- ============================================================
SELECT '5️⃣  2026年5月 波动率最高股票 Top20';

SELECT
    stock_code,
    ROUND(AVG(close_price), 2) AS avg_price,
    ROUND(STDDEV(close_price), 2) AS price_stddev,
    ROUND(STDDEV(close_price) / AVG(close_price) * 100, 2) AS volatility_pct,
    COUNT(*) AS days
FROM stock_daily
WHERE year = 2026 AND month = 5
GROUP BY stock_code
HAVING COUNT(*) >= 10
ORDER BY volatility_pct DESC
LIMIT 20;
