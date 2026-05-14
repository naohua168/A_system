-- ===========================================
-- 数据库迁移脚本 - 在已运行的 Docker MySQL 中执行
-- 使用: docker exec -i mysql mysql -uroot -phadoop123 stock_analysis < migrate.sql
-- ===========================================

-- 1. Stock 表新增字段
ALTER TABLE stock
    ADD COLUMN IF NOT EXISTS `pe` DECIMAL(10,2) DEFAULT NULL COMMENT '市盈率' AFTER `circulated_shares`,
    ADD COLUMN IF NOT EXISTS `pb` DECIMAL(10,2) DEFAULT NULL COMMENT '市净率' AFTER `pe`,
    ADD COLUMN IF NOT EXISTS `total_market_cap` DECIMAL(20,2) DEFAULT NULL COMMENT '总市值（元）' AFTER `pb`,
    ADD COLUMN IF NOT EXISTS `float_market_cap` DECIMAL(20,2) DEFAULT NULL COMMENT '流通市值（元）' AFTER `total_market_cap`;

-- 2. Fund 表新增字段
ALTER TABLE fund
    ADD COLUMN IF NOT EXISTS `scale` DECIMAL(20,2) DEFAULT NULL COMMENT '基金规模（元）' AFTER `accumulated_nav`;

-- 3. 创建基金持仓表
CREATE TABLE IF NOT EXISTS `fund_holding` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `fund_code` VARCHAR(10) NOT NULL COMMENT '基金代码',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) NOT NULL COMMENT '股票名称',
    `ratio` DECIMAL(10,4) DEFAULT NULL COMMENT '持仓占比(%)',
    `rank_num` INT DEFAULT NULL COMMENT '持仓排名',
    `report_date` DATE DEFAULT NULL COMMENT '报告期',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_fund_code` (`fund_code`),
    UNIQUE KEY `uk_fund_stock` (`fund_code`, `stock_code`, `report_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金持仓表';

-- 4. 更新股票数据（PE/PB/市值）
UPDATE stock SET pe=5.82, pb=0.62, total_market_cap=212345678900.00, float_market_cap=189000000000.00 WHERE stock_code='000001';
UPDATE stock SET pe=8.15, pb=0.72, total_market_cap=156000000000.00, float_market_cap=142000000000.00 WHERE stock_code='000002';
UPDATE stock SET pe=13.45, pb=2.81, total_market_cap=478000000000.00, float_market_cap=452000000000.00 WHERE stock_code='000333';
UPDATE stock SET pe=7.82, pb=1.95, total_market_cap=198000000000.00, float_market_cap=186000000000.00 WHERE stock_code='000651';
UPDATE stock SET pe=22.50, pb=1.35, total_market_cap=156000000000.00, float_market_cap=148000000000.00 WHERE stock_code='000725';
UPDATE stock SET pe=22.30, pb=5.65, total_market_cap=612000000000.00, float_market_cap=580000000000.00 WHERE stock_code='000858';
UPDATE stock SET pe=24.56, pb=4.82, total_market_cap=345000000000.00, float_market_cap=320000000000.00 WHERE stock_code='002415';
UPDATE stock SET pe=26.80, pb=5.12, total_market_cap=256000000000.00, float_market_cap=245000000000.00 WHERE stock_code='002475';
UPDATE stock SET pe=18.90, pb=4.55, total_market_cap=890000000000.00, float_market_cap=720000000000.00 WHERE stock_code='300750';
UPDATE stock SET pe=4.35, pb=0.42, total_market_cap=286000000000.00, float_market_cap=268000000000.00 WHERE stock_code='600000';
UPDATE stock SET pe=6.12, pb=0.92, total_market_cap=856000000000.00, float_market_cap=820000000000.00 WHERE stock_code='600036';
UPDATE stock SET pe=55.80, pb=8.92, total_market_cap=356000000000.00, float_market_cap=340000000000.00 WHERE stock_code='600276';
UPDATE stock SET pe=32.50, pb=10.85, total_market_cap=2150000000000.00, float_market_cap=1950000000000.00 WHERE stock_code='600519';
UPDATE stock SET pe=18.60, pb=4.25, total_market_cap=186000000000.00, float_market_cap=175000000000.00 WHERE stock_code='600887';
UPDATE stock SET pe=15.20, pb=3.10, total_market_cap=168000000000.00, float_market_cap=155000000000.00 WHERE stock_code='601012';
UPDATE stock SET pe=4.85, pb=0.52, total_market_cap=356000000000.00, float_market_cap=335000000000.00 WHERE stock_code='601166';
UPDATE stock SET pe=8.90, pb=1.05, total_market_cap=780000000000.00, float_market_cap=750000000000.00 WHERE stock_code='601318';
UPDATE stock SET pe=5.60, pb=0.55, total_market_cap=1680000000000.00, float_market_cap=420000000000.00 WHERE stock_code='601398';
UPDATE stock SET pe=8.30, pb=1.15, total_market_cap=1450000000000.00, float_market_cap=680000000000.00 WHERE stock_code='601857';
UPDATE stock SET pe=35.60, pb=6.80, total_market_cap=278000000000.00, float_market_cap=265000000000.00 WHERE stock_code='603259';

-- 5. 更新基金数据（manager/establish_date/nav/scale）
UPDATE fund SET manager='张坤', establish_date='2018-09-10', nav=1.6850, accumulated_nav=2.1350, scale=69800000000.00 WHERE fund_code='005827';
UPDATE fund SET manager='侯昊', establish_date='2015-05-27', nav=0.9560, accumulated_nav=1.8560, scale=52000000000.00 WHERE fund_code='161725';
UPDATE fund SET manager='刘彦春', establish_date='2006-06-28', nav=2.1250, accumulated_nav=3.8560, scale=39800000000.00 WHERE fund_code='260108';

-- 6. 插入基金持仓数据
INSERT IGNORE INTO `fund_holding` (`fund_code`, `stock_code`, `stock_name`, `ratio`, `rank_num`, `report_date`) VALUES
('005827', '600519', '贵州茅台', 9.85, 1, '2025-12-31'),
('005827', '300750', '宁德时代', 8.56, 2, '2025-12-31'),
('005827', '000858', '五粮液', 7.32, 3, '2025-12-31'),
('005827', '600036', '招商银行', 6.15, 4, '2025-12-31'),
('005827', '601318', '中国平安', 5.88, 5, '2025-12-31'),
('005827', '000333', '美的集团', 5.12, 6, '2025-12-31'),
('005827', '600887', '伊利股份', 4.35, 7, '2025-12-31'),
('005827', '002415', '海康威视', 3.86, 8, '2025-12-31'),
('005827', '601012', '隆基绿能', 3.45, 9, '2025-12-31'),
('005827', '603259', '药明康德', 2.98, 10, '2025-12-31'),
('161725', '600519', '贵州茅台', 16.82, 1, '2025-12-31'),
('161725', '000858', '五粮液', 14.56, 2, '2025-12-31'),
('161725', '600809', '山西汾酒', 13.25, 3, '2025-12-31'),
('161725', '000568', '泸州老窖', 12.35, 4, '2025-12-31'),
('161725', '002304', '洋河股份', 8.56, 5, '2025-12-31'),
('260108', '600519', '贵州茅台', 9.65, 1, '2025-12-31'),
('260108', '000858', '五粮液', 8.25, 2, '2025-12-31'),
('260108', '300750', '宁德时代', 6.82, 3, '2025-12-31'),
('260108', '600036', '招商银行', 5.35, 4, '2025-12-31'),
('260108', '601318', '中国平安', 4.68, 5, '2025-12-31');

-- 7. 插入自选数据（为 admin 用户添加）
INSERT IGNORE INTO `watchlist` (`user_id`, `asset_type`, `asset_code`, `remark`, `sort_order`) VALUES
(1, 0, '600519', '核心资产', 1),
(1, 0, '300750', '新能源龙头', 2),
(1, 0, '000858', '白酒', 3),
(1, 0, '000333', '家电龙头', 4),
(1, 1, '005827', '易方达蓝筹', 1),
(1, 1, '161725', '白酒指数', 2);
