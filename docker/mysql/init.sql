-- ===========================================
-- MySQL 初始化脚本 - 基金股票智能分析系统
-- 注意：种子数据已被移除，所有数据由 data-collector 管道采集写入
-- 保留的种子数据：user（登录必需）、market_index（指数标识符）
-- ===========================================

-- Hive Metastore 数据库（由docker-compose自动创建）
-- CREATE DATABASE IF NOT EXISTS hive_metastore;

-- 业务数据库
CREATE DATABASE IF NOT EXISTS stock_analysis DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE stock_analysis;

-- ========== 用户表 ==========
CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT AUTO_INCREMENT COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL COMMENT '用户名',
    `password` VARCHAR(255) NOT NULL COMMENT '密码（加密）',
    `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    `avatar` VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    `role` TINYINT DEFAULT 0 COMMENT '角色: 0-普通用户, 1-管理员',
    `status` TINYINT DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ========== 股票基础信息表 ==========
CREATE TABLE IF NOT EXISTS `stock` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) NOT NULL COMMENT '股票名称',
    `market` VARCHAR(10) DEFAULT NULL COMMENT '市场: SH/SZ/BJ',
    `industry` VARCHAR(50) DEFAULT NULL COMMENT '所属行业',
    `listing_date` DATE DEFAULT NULL COMMENT '上市日期',
    `total_shares` DECIMAL(20,2) DEFAULT NULL COMMENT '总股本（股）',
    `circulated_shares` DECIMAL(20,2) DEFAULT NULL COMMENT '流通股本（股）',
    `pe` DECIMAL(10,2) DEFAULT NULL COMMENT '市盈率',
    `pb` DECIMAL(10,2) DEFAULT NULL COMMENT '市净率',
    `total_market_cap` DECIMAL(20,2) DEFAULT NULL COMMENT '总市值（元）',
    `float_market_cap` DECIMAL(20,2) DEFAULT NULL COMMENT '流通市值（元）',
    `current_price` DECIMAL(12,4) DEFAULT NULL COMMENT '现价',
    `open_price` DECIMAL(12,4) DEFAULT NULL COMMENT '开盘价',
    `high_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最低价',
    `yesterday_close` DECIMAL(12,4) DEFAULT NULL COMMENT '昨收价',
    `change_percent` DECIMAL(12,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `change_amount` DECIMAL(12,4) DEFAULT NULL COMMENT '涨跌额',
    `turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '换手率(%)',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额(万)',
    `amplitude` DECIMAL(12,4) DEFAULT NULL COMMENT '振幅(%)',
    `limit_up` DECIMAL(12,4) DEFAULT NULL COMMENT '涨停价',
    `limit_down` DECIMAL(12,4) DEFAULT NULL COMMENT '跌停价',
    `vol_ratio` DECIMAL(12,4) DEFAULT NULL COMMENT '量比',
    `pe_static` DECIMAL(12,4) DEFAULT NULL COMMENT '静态市盈率',
    `source` VARCHAR(50) DEFAULT NULL COMMENT '数据来源',
    `status` TINYINT DEFAULT 1 COMMENT '状态: 0-退市/停牌, 1-正常交易',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_code` (`stock_code`),
    KEY `idx_industry` (`industry`),
    KEY `idx_market` (`market`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基础信息表';

-- ========== 基金基础信息表 ==========
CREATE TABLE IF NOT EXISTS `fund` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `fund_code` VARCHAR(10) NOT NULL COMMENT '基金代码',
    `fund_name` VARCHAR(100) NOT NULL COMMENT '基金名称',
    `fund_type` VARCHAR(20) DEFAULT NULL COMMENT '基金类型: 股票型/债券型/混合型/货币型/QDII',
    `company` VARCHAR(100) DEFAULT NULL COMMENT '基金公司',
    `manager` VARCHAR(50) DEFAULT NULL COMMENT '基金经理',
    `establish_date` DATE DEFAULT NULL COMMENT '成立日期',
    `nav` DECIMAL(10,4) DEFAULT NULL COMMENT '最新净值',
    `accumulated_nav` DECIMAL(10,4) DEFAULT NULL COMMENT '累计净值',
    `scale` DECIMAL(20,2) DEFAULT NULL COMMENT '基金规模（元）',
    `status` TINYINT DEFAULT 1 COMMENT '状态: 0-停止, 1-正常',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_fund_code` (`fund_code`),
    KEY `idx_fund_type` (`fund_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金基础信息表';

-- ========== 股票日K线数据表 ==========
CREATE TABLE IF NOT EXISTS `stock_daily` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `open_price` DECIMAL(10,2) DEFAULT NULL COMMENT '开盘价',
    `high_price` DECIMAL(10,2) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(10,2) DEFAULT NULL COMMENT '最低价',
    `close_price` DECIMAL(10,2) DEFAULT NULL COMMENT '收盘价',
    `pre_close` DECIMAL(10,2) DEFAULT NULL COMMENT '昨收价',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量（股）',
    `amount` DECIMAL(20,2) DEFAULT NULL COMMENT '成交额（元）',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `turnover_rate` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率(%)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_date` (`stock_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日K线数据表';

-- ========== 基金净值历史表 ==========
CREATE TABLE IF NOT EXISTS `fund_nav` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `fund_code` VARCHAR(10) NOT NULL COMMENT '基金代码',
    `nav_date` DATE NOT NULL COMMENT '净值日期',
    `nav` DECIMAL(10,4) DEFAULT NULL COMMENT '单位净值',
    `accumulated_nav` DECIMAL(10,4) DEFAULT NULL COMMENT '累计净值',
    `daily_return` DECIMAL(10,4) DEFAULT NULL COMMENT '日收益率(%)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_fund_date` (`fund_code`, `nav_date`),
    KEY `idx_nav_date` (`nav_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金净值历史表';

-- ========== 自选表 ==========
CREATE TABLE IF NOT EXISTS `watchlist` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `asset_type` TINYINT NOT NULL COMMENT '资产类型: 0-股票, 1-基金',
    `asset_code` VARCHAR(10) NOT NULL COMMENT '资产代码（股票代码/基金代码）',
    `remark` VARCHAR(200) DEFAULT NULL COMMENT '备注',
    `sort_order` INT DEFAULT 0 COMMENT '排序',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_asset` (`user_id`, `asset_type`, `asset_code`),
    KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选表';

-- ========== 分析结果表 ==========
CREATE TABLE IF NOT EXISTS `analysis_result` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `asset_type` TINYINT NOT NULL COMMENT '资产类型: 0-股票, 1-基金',
    `asset_code` VARCHAR(10) NOT NULL COMMENT '资产代码',
    `analysis_type` VARCHAR(50) NOT NULL COMMENT '分析类型: TECHNICAL/CHANLUN/QUANTITATIVE',
    `result_json` JSON DEFAULT NULL COMMENT '分析结果JSON',
    `summary` VARCHAR(500) DEFAULT NULL COMMENT '分析摘要',
    `analysis_date` DATE NOT NULL COMMENT '分析日期',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_asset_date` (`asset_code`, `analysis_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析结果表';

-- ========== AI对话记录表 ==========
CREATE TABLE IF NOT EXISTS `ai_chat` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `session_id` VARCHAR(50) NOT NULL COMMENT '会话ID',
    `role` TINYINT NOT NULL COMMENT '角色: 0-用户, 1-AI',
    `content` TEXT NOT NULL COMMENT '对话内容',
    `asset_code` VARCHAR(10) DEFAULT NULL COMMENT '关联资产代码（可选）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_session` (`session_id`),
    KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI对话记录表';

-- ========== 插入初始化用户（系统必需，用于登录） ==========
INSERT INTO `user` (`username`, `password`, `email`, `role`) VALUES
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'admin@stock.com', 1),
('test', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'test@stock.com', 0);

-- ========== 市场指数基础信息表 ==========
CREATE TABLE IF NOT EXISTS `market_index` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `index_code` VARCHAR(20) NOT NULL COMMENT '指数代码',
    `index_name` VARCHAR(50) NOT NULL COMMENT '指数名称',
    `market` VARCHAR(10) DEFAULT NULL COMMENT '市场: SH/SZ/HK/US',
    `category` VARCHAR(20) DEFAULT NULL COMMENT '分类: A/HK/US/global',
    `source` VARCHAR(20) DEFAULT NULL COMMENT '数据源',
    `status` TINYINT DEFAULT 1 COMMENT '状态',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_index_code` (`index_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场指数基础信息表';

-- 指数标识符（真实代码，非种子模拟数据）
INSERT INTO `market_index` (`index_code`, `index_name`, `market`, `category`) VALUES
('000001', '上证指数', 'SH', 'A'),
('399001', '深证成指', 'SZ', 'A'),
('399006', '创业板指', 'SZ', 'A'),
('000688', '科创50', 'SH', 'A'),
('000300', '沪深300', 'SH', 'A'),
('000016', '上证50', 'SH', 'A'),
('399905', '中证500', 'SZ', 'A'),
('HSI', '恒生指数', 'HK', 'HK'),
('DJI', '道琼斯', 'US', 'US'),
('IXIC', '纳斯达克', 'US', 'US'),
('SPX', '标普500', 'US', 'US');

-- ========== 指数日K线数据表 ==========
CREATE TABLE IF NOT EXISTS `index_daily` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `index_code` VARCHAR(20) NOT NULL COMMENT '指数代码',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `open_point` DECIMAL(12,4) DEFAULT NULL COMMENT '开盘点位',
    `high_point` DECIMAL(12,4) DEFAULT NULL COMMENT '最高点位',
    `low_point` DECIMAL(12,4) DEFAULT NULL COMMENT '最低点位',
    `close_point` DECIMAL(12,4) DEFAULT NULL COMMENT '收盘点位',
    `pre_close` DECIMAL(12,4) DEFAULT NULL COMMENT '昨收点位',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量',
    `amount` DECIMAL(20,2) DEFAULT NULL COMMENT '成交额',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_index_date` (`index_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指数日K线数据表';

-- ========== 基金持仓表 ==========
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

-- ========== 信号层数据表 ==========
CREATE TABLE IF NOT EXISTS `signal_hot_reason` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `reason` VARCHAR(500) DEFAULT NULL COMMENT '题材归因标签',
    `change_pct` DECIMAL(10,4) DEFAULT NULL COMMENT '涨幅%',
    `turnover_pct` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率%',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_code` (`trade_date`, `stock_code`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题材归因表（同花顺热点）';

CREATE TABLE IF NOT EXISTS `signal_dragon_tiger` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `reason` VARCHAR(200) DEFAULT NULL COMMENT '上榜原因',
    `net_buy_wan` DECIMAL(20,2) DEFAULT NULL COMMENT '龙虎榜净买额(万)',
    `buy_wan` DECIMAL(20,2) DEFAULT NULL COMMENT '总买入额(万)',
    `sell_wan` DECIMAL(20,2) DEFAULT NULL COMMENT '总卖出额(万)',
    `change_pct` DECIMAL(10,4) DEFAULT NULL COMMENT '当日涨跌幅%',
    `turnover_pct` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率%',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_code` (`trade_date`, `stock_code`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜数据表';

CREATE TABLE IF NOT EXISTS `signal_northbound` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `time` VARCHAR(10) DEFAULT NULL COMMENT '分钟时间 HH:MM',
    `hgt_yi` DECIMAL(20,4) DEFAULT NULL COMMENT '沪股通净流入(亿)',
    `sgt_yi` DECIMAL(20,4) DEFAULT NULL COMMENT '深股通净流入(亿)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_time` (`trade_date`, `time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='北向资金数据表';

CREATE TABLE IF NOT EXISTS `signal_lockup` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `lockup_date` DATE NOT NULL COMMENT '解禁日期',
    `lockup_type` VARCHAR(50) DEFAULT NULL COMMENT '限售股类型',
    `shares` DECIMAL(20,2) DEFAULT NULL COMMENT '解禁数量',
    `float_ratio` DECIMAL(10,4) DEFAULT NULL COMMENT '占流通股比例%',
    `is_upcoming` TINYINT DEFAULT 1 COMMENT '1=未来待解禁, 0=历史已解禁',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_date` (`lockup_date`),
    KEY `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='限售解禁预警表';

CREATE TABLE IF NOT EXISTS `signal_daily_industry` (
    `id` BIGINT AUTO_INCREMENT COMMENT '主键ID',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `rank_num` INT DEFAULT NULL COMMENT '排名',
    `industry_name` VARCHAR(50) NOT NULL COMMENT '行业名称',
    `change_pct` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅%',
    `turnover_yi` DECIMAL(20,4) DEFAULT NULL COMMENT '总成交额(亿)',
    `net_inflow_yi` DECIMAL(20,4) DEFAULT NULL COMMENT '净流入(亿)',
    `up_count` INT DEFAULT NULL COMMENT '上涨家数',
    `down_count` INT DEFAULT NULL COMMENT '下跌家数',
    `leader` VARCHAR(50) DEFAULT NULL COMMENT '领涨股',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行业涨跌排行表';

-- ========== 自选数据（admin 用户示例） ==========
INSERT INTO `watchlist` (`user_id`, `asset_type`, `asset_code`, `remark`, `sort_order`) VALUES
(1, 0, '600519', '核心资产', 1),
(1, 0, '300750', '新能源龙头', 2),
(1, 0, '000858', '白酒', 3),
(1, 0, '000333', '家电龙头', 4),
(1, 1, '005827', '易方达蓝筹', 1),
(1, 1, '161725', '白酒指数', 2);
