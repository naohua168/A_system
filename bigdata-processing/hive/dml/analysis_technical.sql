-- ============================================================
-- Hive 分析查询: 技术指标计算
-- 使用纯 SQL 在 Hive 中计算移动均线(MA)和RSI等技术指标
-- 依赖 Hive 2.1+ 窗口函数支持
-- ============================================================

USE stock_analysis;

-- 启用动态分区（写结果表用）
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

-- ============================================================
-- 1. 移动均线 (MA): MA5 / MA10 / MA20 / MA60
-- 使用 Hive AVG() 窗口函数按日期排序计算
-- ============================================================
SELECT '1️⃣  000001 (平安银行) 移动均线计算 (MA5/MA10/MA20/MA60)';

WITH ordered_prices AS (
    SELECT
        stock_code,
        trade_date,
        close_price,
        ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY trade_date) AS rn
    FROM stock_daily
    WHERE stock_code = '000001'
      AND trade_date >= DATE_SUB(CURRENT_DATE, 120)
)
SELECT
    stock_code,
    trade_date,
    ROUND(close_price, 2) AS close_price,
    ROUND(AVG(close_price) OVER (
        PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ), 2) AS ma5,
    ROUND(AVG(close_price) OVER (
        PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ), 2) AS ma10,
    ROUND(AVG(close_price) OVER (
        PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ), 2) AS ma20,
    ROUND(AVG(close_price) OVER (
        PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ), 2) AS ma60,
    -- 金叉/死叉信号判断 (MA5 vs MA20)
    CASE
        WHEN AVG(close_price) OVER (
            PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) > AVG(close_price) OVER (
            PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) THEN 'golden'
        WHEN AVG(close_price) OVER (
            PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) < AVG(close_price) OVER (
            PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) THEN 'death'
        ELSE 'none'
    END AS ma_cross_signal
FROM ordered_prices
ORDER BY trade_date DESC
LIMIT 30;

-- ============================================================
-- 2. RSI 指标计算 (14日)
-- RSI = 100 - 100/(1 + avg_gain/avg_loss)
-- ============================================================
SELECT '2️⃣  000001 RSI(14) 指标计算';

WITH price_changes AS (
    SELECT
        stock_code,
        trade_date,
        close_price,
        close_price - LAG(close_price, 1) OVER (
            PARTITION BY stock_code ORDER BY trade_date
        ) AS price_change
    FROM stock_daily
    WHERE stock_code = '000001'
      AND trade_date >= DATE_SUB(CURRENT_DATE, 90)
),
gains_losses AS (
    SELECT
        stock_code,
        trade_date,
        close_price,
        CASE WHEN price_change > 0 THEN price_change ELSE 0 END AS gain,
        CASE WHEN price_change < 0 THEN ABS(price_change) ELSE 0 END AS loss
    FROM price_changes
    WHERE price_change IS NOT NULL
),
avg_gains_losses AS (
    SELECT
        stock_code,
        trade_date,
        close_price,
        AVG(gain) OVER (
            PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS avg_gain,
        AVG(loss) OVER (
            PARTITION BY stock_code ORDER BY trade_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS avg_loss
    FROM gains_losses
)
SELECT
    stock_code,
    trade_date,
    ROUND(close_price, 2) AS close_price,
    ROUND(avg_gain, 4) AS avg_gain_14,
    ROUND(avg_loss, 4) AS avg_loss_14,
    ROUND(
        CASE
            WHEN avg_loss = 0 THEN 100
            ELSE 100 - 100 / (1 + avg_gain / avg_loss)
        END
    , 2) AS rsi_14,
    CASE
        WHEN (CASE WHEN avg_loss = 0 THEN 100 ELSE 100 - 100 / (1 + avg_gain / avg_loss) END) > 70 THEN '超买'
        WHEN (CASE WHEN avg_loss = 0 THEN 100 ELSE 100 - 100 / (1 + avg_gain / avg_loss) END) < 30 THEN '超卖'
        ELSE '正常'
    END AS rsi_signal
FROM avg_gains_losses
ORDER BY trade_date DESC
LIMIT 20;

-- ============================================================
-- 3. 全市场 MA 金叉/死叉信号统计
-- 最新交易日的信号分布
-- ============================================================
SELECT '3️⃣  全市场最新 MA 金叉/死叉信号统计';

WITH latest_date AS (
    SELECT MAX(trade_date) AS max_date FROM stock_daily
),
ma_signals AS (
    SELECT
        d.stock_code,
        d.trade_date,
        d.close_price,
        AVG(d.close_price) OVER (
            PARTITION BY d.stock_code ORDER BY d.trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS ma5,
        AVG(d.close_price) OVER (
            PARTITION BY d.stock_code ORDER BY d.trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS ma20
    FROM stock_daily d
    JOIN latest_date l ON d.trade_date = l.max_date
)
SELECT
    CASE
        WHEN ma5 > ma20 THEN '金叉 (MA5 > MA20)'
        WHEN ma5 < ma20 THEN '死叉 (MA5 < MA20)'
        ELSE '持平'
    END AS signal_type,
    COUNT(*) AS stock_count,
    ROUND(AVG(close_price), 2) AS avg_price,
    ROUND(AVG(ma5 - ma20), 2) AS avg_spread
FROM ma_signals
WHERE ma5 IS NOT NULL AND ma20 IS NOT NULL
GROUP BY
    CASE
        WHEN ma5 > ma20 THEN '金叉 (MA5 > MA20)'
        WHEN ma5 < ma20 THEN '死叉 (MA5 < MA20)'
        ELSE '持平'
    END;

-- ============================================================
-- 4. 写入预计算结果表: MA信号
-- ============================================================
-- INSERT OVERWRITE TABLE precomputed_ma_signal
-- SELECT ...;  -- 实际运行时取消注释
