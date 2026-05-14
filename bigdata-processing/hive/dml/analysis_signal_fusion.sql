-- ============================================================
-- Hive 分析查询: 信号融合分析
-- 多维度信号 JOIN 综合评分，产生推荐排序
-- 数据源: 技术指标 + 资金流向 + 题材热点
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 个股综合信号评分
-- 融合: 涨跌幅/换手率/技术指标/资金流向/题材热点
-- ============================================================
SELECT '1️⃣  个股综合信号评分 Top30';

WITH latest_trade AS (
    SELECT MAX(trade_date) AS max_date FROM stock_daily
),
latest_prices AS (
    SELECT
        d.stock_code,
        d.trade_date,
        d.close_price,
        d.change_pct,
        d.turnover,
        d.volume,
        d.amount,
        AVG(d.close_price) OVER (
            PARTITION BY d.stock_code ORDER BY d.trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS ma5,
        AVG(d.close_price) OVER (
            PARTITION BY d.stock_code ORDER BY d.trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS ma20
    FROM stock_daily d
    CROSS JOIN latest_trade lt
    WHERE d.trade_date >= DATE_SUB(lt.max_date, 30)
),
latest_snapshot AS (
    SELECT DISTINCT stock_code
    FROM latest_prices
    WHERE trade_date = (SELECT max_date FROM latest_trade)
),
score_base AS (
    SELECT
        lp.stock_code,
        lp.close_price,
        lp.change_pct,
        lp.turnover,
        lp.volume,
        lp.amount,
        lp.ma5,
        lp.ma20,
        -- 动量评分: 近5日涨幅
        ROUND(lp.change_pct, 2) AS momentum_score
    FROM latest_prices lp
    JOIN latest_snapshot ls ON lp.stock_code = ls.stock_code
    WHERE lp.trade_date = (SELECT max_date FROM latest_trade)
)
SELECT
    s.stock_code,
    b.name,
    b.industry,
    s.close_price,
    s.change_pct,
    s.turnover,
    ROUND(s.amount / 100000000, 2) AS amount_yi,
    -- 技术面评分: MA5 > MA20 加分
    CASE WHEN s.ma5 > s.ma20 THEN 10 ELSE -5 END AS tech_score,
    -- 成交量评分: 放量>均量加分
    CASE WHEN s.volume > 0 THEN 5 ELSE 0 END AS volume_score,
    -- 综合评分 (各项相加)
    ROUND(
        CASE WHEN s.ma5 > s.ma20 THEN 10 ELSE -5 END
        + CASE WHEN s.change_pct > 3 THEN 15 WHEN s.change_pct > 0 THEN 5 ELSE -10 END
        + CASE WHEN s.turnover > 5 THEN 8 ELSE 0 END
    , 0) AS composite_score
FROM score_base s
JOIN stock_basic b ON s.stock_code = b.code
WHERE b.industry IS NOT NULL AND s.close_price > 0
ORDER BY composite_score DESC
LIMIT 30;

-- ============================================================
-- 2. 信号表 JOIN: 融合题材归因 + 个股信号 + 行业对比
-- 需要 signal_tables.sql 中创建的表存在
-- ============================================================
SELECT '2️⃣  信号融合: 题材 + 资金 + 行业 (JOIN 多表)';

WITH latest_signal AS (
    SELECT stock_code, MAX(fetch_date) AS max_date
    FROM signal_stock
    GROUP BY stock_code
)
SELECT
    ss.stock_code,
    ss.concept_tags,
    ss.fund_flow_main,
    ss.dragon_tiger_count,
    hr.reason AS hot_reason,
    hr.zhangfu AS hot_zhangfu,
    ind.name AS industry_name,
    ind.change_pct AS industry_change
FROM signal_stock ss
JOIN latest_signal ls ON ss.stock_code = ls.stock_code AND ss.fetch_date = ls.max_date
LEFT JOIN signal_hot_reason hr ON ss.stock_code = hr.code AND hr.fetch_date = ls.max_date
LEFT JOIN signal_industry ind ON 1=1  -- 行业对比表暂无直接股票级关联
WHERE ss.fund_flow_main > 5000       -- 主力资金净流入 > 5000万
ORDER BY ss.fund_flow_main DESC
LIMIT 20;

-- ============================================================
-- 3. 多因子筛选: 同时满足多个条件的强势股票
-- ============================================================
SELECT '3️⃣  多因子强势筛选 (涨+放量+资金流入)';

SELECT
    d.stock_code,
    b.name,
    b.industry,
    d.change_pct,
    d.turnover,
    ROUND(d.amount / 100000000, 2) AS amount_yi,
    d.close_price
FROM stock_daily d
JOIN stock_basic b ON d.stock_code = b.code
WHERE d.trade_date = (SELECT MAX(trade_date) FROM stock_daily)
  AND d.change_pct > 0          -- 上涨
  AND d.turnover > 3             -- 换手率 > 3%
  AND d.amount > 100000000      -- 成交额 > 1亿
  AND d.close_price > 0
  AND b.industry IS NOT NULL
ORDER BY d.change_pct DESC
LIMIT 30;

-- ============================================================
-- 4. 北向资金与行业涨跌关联
-- 需要 signal_tables.sql 中的 northbound 表
-- ============================================================
SELECT '4️⃣  北向资金流向 vs 行业涨跌';

SELECT
    nb.time,
    nb.hgt_yi + nb.sgt_yi AS total_northbound_yi,
    ind.name AS industry_name,
    ind.change_pct AS industry_change_pct,
    ind.net_inflow_yi AS industry_inflow_yi
FROM signal_northbound nb
CROSS JOIN signal_industry ind
WHERE nb.time = ind.fetch_date
  AND ind.change_pct IS NOT NULL
ORDER BY ind.change_pct DESC
LIMIT 20;
