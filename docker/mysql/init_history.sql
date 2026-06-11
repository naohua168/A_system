-- ===========================================
-- stock_history 初始化 - 每日收盘快照归档库
-- 与 stock_analysis（业务库）完全分离
-- ===========================================

CREATE DATABASE IF NOT EXISTS stock_history
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE stock_history;

-- 1. 个股日线快照 (5542 行/天)
CREATE TABLE IF NOT EXISTS stock_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    open_price DECIMAL(12,2),
    close_price DECIMAL(12,2),
    high_price DECIMAL(12,2),
    low_price DECIMAL(12,2),
    volume BIGINT,
    change_pct DECIMAL(8,4),
    turnover_pct DECIMAL(8,4),
    pe_ttm DECIMAL(12,4),
    pb DECIMAL(12,4),
    mcap_yi DECIMAL(16,4),
    UNIQUE KEY uk_stock_date (stock_code, trade_date),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个股日线快照';

-- 2. 指数日线快照 (5 行/天)
CREATE TABLE IF NOT EXISTS index_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    index_code VARCHAR(10) NOT NULL,
    index_name VARCHAR(50),
    close_point DECIMAL(12,2),
    change_pct DECIMAL(8,4),
    open_point DECIMAL(12,2),
    high_point DECIMAL(12,2),
    low_point DECIMAL(12,2),
    volume BIGINT,
    pre_close DECIMAL(12,2),
    UNIQUE KEY uk_idx_date (index_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指数日线快照';

-- 3. 行业日线 (99 行/天)
CREATE TABLE IF NOT EXISTS industry_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    industry_name VARCHAR(50),
    change_pct DECIMAL(8,4),
    stock_count INT,
    total_amount DECIMAL(16,2),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行业日线';

-- 4. 北向资金日线 (1 行/天)
CREATE TABLE IF NOT EXISTS northbound_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    hgt_yi DECIMAL(12,4),
    sgt_yi DECIMAL(12,4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='北向资金日线';

-- 5. 题材热点 (~100 行/天)
CREATE TABLE IF NOT EXISTS hot_reason_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(10),
    stock_name VARCHAR(50),
    reason VARCHAR(500),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题材热点日线';

-- 6. 龙虎榜 (~250 行/天)
CREATE TABLE IF NOT EXISTS dragon_tiger_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(10),
    stock_name VARCHAR(50),
    reason VARCHAR(500),
    net_buy_wan DECIMAL(20,4),
    change_pct DECIMAL(8,4),
    turnover_pct DECIMAL(8,4),
    buy_wan DECIMAL(20,4),
    sell_wan DECIMAL(20,4),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜日线';

-- 7. 资讯归档（新闻持久化，支持历史查询）
CREATE TABLE IF NOT EXISTS info_news (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    news_id VARCHAR(64) UNIQUE,
    title VARCHAR(500),
    summary TEXT,
    source VARCHAR(50) COMMENT 'cls: 财联社, global: 全球资讯',
    publish_time DATETIME,
    content TEXT,
    url VARCHAR(500),
    INDEX idx_publish_time (publish_time),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯归档';
