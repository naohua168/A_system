-- ===========================================
-- MySQL 初始化脚本 - 基金股票智能分析系统
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

-- ========== 插入测试用户 ==========
INSERT INTO `user` (`username`, `password`, `email`, `role`) VALUES
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'admin@stock.com', 1),
('test', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'test@stock.com', 0);

-- ========== 插入示例股票数据 ==========
INSERT INTO `stock` (`stock_code`, `stock_name`, `market`, `industry`) VALUES
('000001', '平安银行', 'SZ', '银行'),
('000002', '万科A', 'SZ', '房地产'),
('000333', '美的集团', 'SZ', '家用电器'),
('000651', '格力电器', 'SZ', '家用电器'),
('000725', '京东方A', 'SZ', '电子'),
('000858', '五粮液', 'SZ', '食品饮料'),
('002415', '海康威视', 'SZ', '电子'),
('002475', '立讯精密', 'SZ', '电子'),
('300750', '宁德时代', 'SZ', '电力设备'),
('600000', '浦发银行', 'SH', '银行'),
('600036', '招商银行', 'SH', '银行'),
('600276', '恒瑞医药', 'SH', '医药生物'),
('600519', '贵州茅台', 'SH', '食品饮料'),
('600887', '伊利股份', 'SH', '食品饮料'),
('601012', '隆基绿能', 'SH', '电力设备'),
('601166', '兴业银行', 'SH', '银行'),
('601318', '中国平安', 'SH', '非银金融'),
('601398', '工商银行', 'SH', '银行'),
('601857', '中国石油', 'SH', '石油石化'),
('603259', '药明康德', 'SH', '医药生物');

-- ========== 插入示例基金数据 ==========
INSERT INTO `fund` (`fund_code`, `fund_name`, `fund_type`, `company`) VALUES
('000001', '华夏成长混合', '混合型', '华夏基金管理有限公司'),
('002001', '华夏回报混合A', '混合型', '华夏基金管理有限公司'),
('005827', '易方达蓝筹精选混合', '混合型', '易方达基金管理有限公司'),
('007493', '中欧创新成长混合A', '混合型', '中欧基金管理有限公司'),
('008286', '易方达研究精选股票', '股票型', '易方达基金管理有限公司'),
('110011', '易方达中小盘混合', '混合型', '易方达基金管理有限公司'),
('161725', '招商中证白酒指数(LOF)A', '股票型', '招商基金管理有限公司'),
('163402', '兴全趋势投资混合(LOF)', '混合型', '兴证全球基金管理有限公司'),
('260108', '景顺长城新兴成长混合', '混合型', '景顺长城基金管理有限公司'),
('519772', '交银新生活力灵活配置混合', '混合型', '交银施罗德基金管理有限公司');

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

-- ========== 插入指数基础信息 ==========
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
