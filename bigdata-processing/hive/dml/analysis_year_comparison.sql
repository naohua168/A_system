-- ============================================================
-- Hive 分析查询: 多年同比分析
-- 对比今年与去年同期指定区间的涨跌幅
-- 基于 stock_daily 分区表 (Parquet)
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 个股今年 vs 去年同月涨跌幅对比
-- ============================================================
SELECT '1️⃣  个股月同比涨跌幅对比 (2026年5月 vs 2025年5月)';

WITH this_year AS (
    SELECT
        stock_code,
        ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS month_return,
        COUNT(*) AS trade_days
    FROM stock_daily
    WHERE year = 2026 AND month = 5
    GROUP BY stock_code
    HAVING COUNT(*) >= 10
),
last_year AS (
    SELECT
        stock_code,
        ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS month_return,
        COUNT(*) AS trade_days
    FROM stock_daily
    WHERE year = 2025 AND month = 5
    GROUP BY stock_code
    HAVING COUNT(*) >= 10
)
SELECT
    t.stock_code,
    b.name,
    b.industry,
    t.month_return AS return_2026,
    l.month_return AS return_2025,
    ROUND(t.month_return - l.month_return, 2) AS change_pct_diff,
    CASE
        WHEN t.month_return > l.month_return THEN '跑赢去年'
        WHEN t.month_return < l.month_return THEN '跑输去年'
        ELSE '持平'
    END AS yoy_comparison
FROM this_year t
JOIN last_year l ON t.stock_code = l.stock_code
JOIN stock_basic b ON t.stock_code = b.code
ORDER BY change_pct_diff DESC
LIMIT 30;

-- ============================================================
-- 2. 行业同比涨跌幅对比
-- ============================================================
SELECT '2️⃣  行业同比涨跌幅 (2026年5月 vs 2025年5月)';

WITH this_year AS (
    SELECT
        b.industry,
        ROUND(AVG((d.close_price - d.open_price) / d.open_price * 100), 2) AS avg_daily_change
    FROM stock_daily d
    JOIN stock_basic b ON d.stock_code = b.code
    WHERE d.year = 2026 AND d.month = 5
      AND b.industry IS NOT NULL
      AND d.open_price > 0
    GROUP BY b.industry
),
last_year AS (
    SELECT
        b.industry,
        ROUND(AVG((d.close_price - d.open_price) / d.open_price * 100), 2) AS avg_daily_change
    FROM stock_daily d
    JOIN stock_basic b ON d.stock_code = b.code
    WHERE d.year = 2025 AND d.month = 5
      AND b.industry IS NOT NULL
      AND d.open_price > 0
    GROUP BY b.industry
)
SELECT
    t.industry,
    t.avg_daily_change AS change_2026,
    l.avg_daily_change AS change_2025,
    ROUND(t.avg_daily_change - l.avg_daily_change, 2) AS diff
FROM this_year t
JOIN last_year l ON t.industry = l.industry
ORDER BY diff DESC;

-- ============================================================
-- 3. 季度同比对比 (今年Q2 vs 去年Q2)
-- ============================================================
SELECT '3️⃣  2026年Q2 vs 2025年Q2 个股累计涨幅对比 Top20';

WITH this_q AS (
    SELECT
        stock_code,
        ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS q_return
    FROM stock_daily
    WHERE year = 2026 AND CAST(month AS INT) BETWEEN 4 AND 6
    GROUP BY stock_code
    HAVING COUNT(*) >= 30
),
last_q AS (
    SELECT
        stock_code,
        ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS q_return
    FROM stock_daily
    WHERE year = 2025 AND CAST(month AS INT) BETWEEN 4 AND 6
    GROUP BY stock_code
    HAVING COUNT(*) >= 30
)
SELECT
    t.stock_code,
    b.name,
    t.q_return AS return_2026q2,
    l.q_return AS return_2025q2,
    ROUND(t.q_return - l.q_return, 2) AS improvement
FROM this_q t
JOIN last_q l ON t.stock_code = l.stock_code
JOIN stock_basic b ON t.stock_code = b.code
ORDER BY improvement DESC
LIMIT 20;

-- ============================================================
-- 4. 年初至今 vs 去年同期 累计涨幅
-- ============================================================
SELECT '4️⃣  年初至今累计涨幅 vs 去年同期 Top20';

WITH ytd_this AS (
    SELECT
        stock_code,
        ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS ytd_return
    FROM stock_daily
    WHERE year = 2026 AND CAST(month AS INT) <= 5
    GROUP BY stock_code
    HAVING COUNT(*) >= 50
),
ytd_last AS (
    SELECT
        stock_code,
        ROUND(((MAX(close_price) - MIN(close_price)) / MIN(close_price)) * 100, 2) AS ytd_return
    FROM stock_daily
    WHERE year = 2025 AND CAST(month AS INT) <= 5
    GROUP BY stock_code
    HAVING COUNT(*) >= 50
)
SELECT
    t.stock_code,
    b.name,
    b.industry,
    t.ytd_return AS ytd_2026,
    l.ytd_return AS ytd_2025,
    ROUND(t.ytd_return - l.ytd_return, 2) AS improvement
FROM ytd_this t
JOIN ytd_last l ON t.stock_code = l.stock_code
JOIN stock_basic b ON t.stock_code = b.code
ORDER BY improvement DESC
LIMIT 20;

-- ============================================================
-- 5. 写入预计算结果表: 年收益率
-- ============================================================
-- INSERT OVERWRITE TABLE precomputed_yearly_return
-- SELECT ...;  -- 实际运行时取消注释
