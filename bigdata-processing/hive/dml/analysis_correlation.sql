-- ============================================================
-- Hive 分析查询: 相关系数分析
-- 基于 stock_daily 分区表通过自关联计算股票对间的价格相关性
-- 使用 Pearson 相关系数公式: 
--   r = (nΣxy - ΣxΣy) / sqrt((nΣx² - (Σx)²)(nΣy² - (Σy)²))
-- ============================================================

USE stock_analysis;

-- 设置动态分区（如果需要写入结果表）
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

-- ============================================================
-- 1. 单对股票相关性分析 (指定两只股票)
-- 计算过去一年两只股票的收盘价 Pearson 相关系数
-- ============================================================
SELECT '1️⃣  股票对相关性计算: 000001 (平安银行) vs 600519 (贵州茅台)';

WITH daily_prices AS (
    SELECT
        a.trade_date,
        a.close_price AS price_a,
        b.close_price AS price_b
    FROM stock_daily a
    JOIN stock_daily b
      ON a.trade_date = b.trade_date
     AND a.stock_code = '000001'
     AND b.stock_code = '600519'
    WHERE a.trade_date >= DATE_SUB(CURRENT_DATE, 365)
)
SELECT
    '000001' AS stock_a,
    '600519' AS stock_b,
    ROUND(
        (COUNT(*) * SUM(price_a * price_b) - SUM(price_a) * SUM(price_b))
        / (
            SQRT(COUNT(*) * SUM(price_a * price_a) - SUM(price_a) * SUM(price_a))
            * SQRT(COUNT(*) * SUM(price_b * price_b) - SUM(price_b) * SUM(price_b))
        )
    , 4) AS pearson_correlation,
    COUNT(*) AS sample_days
FROM daily_prices
WHERE price_a IS NOT NULL AND price_b IS NOT NULL
  AND price_a > 0 AND price_b > 0;

-- ============================================================
-- 2. 同行业股票相关性排行
-- 找出与指定股票相关性最高的同行业股票 Top10
-- ============================================================
SELECT '2️⃣  与 000001 同行业相关性最高的股票 Top10';

WITH target_industry AS (
    SELECT industry FROM stock_basic WHERE code = '000001'
),
daily_stats AS (
    SELECT
        a.stock_code AS stock_a,
        b.stock_code AS stock_b,
        a.trade_date,
        a.close_price AS price_a,
        b.close_price AS price_b
    FROM stock_daily a
    JOIN stock_daily b
      ON a.trade_date = b.trade_date
     AND a.stock_code = '000001'
     AND b.stock_code != '000001'
    WHERE a.trade_date >= DATE_SUB(CURRENT_DATE, 365)
      AND a.close_price > 0 AND b.close_price > 0
),
correlation AS (
    SELECT
        stock_b,
        ROUND(
            (COUNT(*) * SUM(price_a * price_b) - SUM(price_a) * SUM(price_b))
            / (
                SQRT(COUNT(*) * SUM(price_a * price_a) - SUM(price_a) * SUM(price_a))
                * SQRT(COUNT(*) * SUM(price_b * price_b) - SUM(price_b) * SUM(price_b))
            )
        , 4) AS correlation_r,
        COUNT(*) AS days
    FROM daily_stats
    GROUP BY stock_b
    HAVING COUNT(*) >= 60  -- 至少60个交易日
)
SELECT
    c.stock_b,
    b.name,
    b.industry,
    c.correlation_r,
    c.days
FROM correlation c
JOIN stock_basic b ON c.stock_b = b.code
JOIN target_industry t ON b.industry = t.industry
WHERE c.correlation_r > 0.5
ORDER BY c.correlation_r DESC
LIMIT 10;

-- ============================================================
-- 3. 全市场股票相关性矩阵（行业间）
-- 计算不同行业代表性股票间的平均相关性
-- ============================================================
SELECT '3️⃣  行业间平均相关性矩阵';

WITH ranked_stocks AS (
    -- 每个行业选市值最大的前3只股票作为代表
    SELECT
        code,
        industry,
        ROW_NUMBER() OVER (PARTITION BY industry ORDER BY total_market_cap DESC) AS rn
    FROM stock_basic
    WHERE industry IS NOT NULL AND total_market_cap > 0
),
representatives AS (
    SELECT code, industry FROM ranked_stocks WHERE rn <= 3
),
daily_pairs AS (
    SELECT
        a.industry AS industry_a,
        b.industry AS industry_b,
        a.code AS stock_a,
        b.code AS stock_b,
        da.trade_date,
        da.close_price AS price_a,
        db.close_price AS price_b
    FROM representatives a
    JOIN representatives b ON a.industry < b.industry  -- 避免重复对
    JOIN stock_daily da ON da.stock_code = a.code
    JOIN stock_daily db ON db.stock_code = b.code AND db.trade_date = da.trade_date
    WHERE da.year = 2026 AND da.close_price > 0 AND db.close_price > 0
)
SELECT
    industry_a,
    industry_b,
    ROUND(AVG(corr_r), 4) AS avg_correlation,
    COUNT(*) AS pair_count
FROM (
    SELECT
        industry_a,
        industry_b,
        stock_a,
        stock_b,
        (COUNT(*) * SUM(price_a * price_b) - SUM(price_a) * SUM(price_b))
        / (
            SQRT(COUNT(*) * SUM(price_a * price_a) - SUM(price_a) * SUM(price_a))
            * SQRT(COUNT(*) * SUM(price_b * price_b) - SUM(price_b) * SUM(price_b))
        ) AS corr_r
    FROM daily_pairs
    GROUP BY industry_a, industry_b, stock_a, stock_b
    HAVING COUNT(*) >= 30
) t
GROUP BY industry_a, industry_b
HAVING COUNT(*) >= 1
ORDER BY avg_correlation DESC;

-- ============================================================
-- 4. 写入预计算结果表（供批处理使用）
-- ============================================================
-- INSERT OVERWRITE TABLE precomputed_correlation
-- SELECT ...;  -- 实际运行时取消注释
