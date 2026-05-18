-- 多周期K线表（8种周期）
-- 分钟级: 1min, 5min, 15min, 30min, 60min
-- 日/周/月: daily, weekly, monthly

CREATE TABLE IF NOT EXISTS stock_kline_1min (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_time DATETIME NOT NULL COMMENT '交易时间',
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(20,2) DEFAULT 0,
    source VARCHAR(20) DEFAULT 'sina',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_time (stock_code, trade_time),
    INDEX idx_stock_code (stock_code),
    INDEX idx_trade_time (trade_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='1分钟K线';

CREATE TABLE IF NOT EXISTS stock_kline_5min (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_time DATETIME NOT NULL,
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(20,2) DEFAULT 0,
    source VARCHAR(20) DEFAULT 'sina',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_time (stock_code, trade_time),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='5分钟K线';

CREATE TABLE IF NOT EXISTS stock_kline_15min (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_time DATETIME NOT NULL,
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(20,2) DEFAULT 0,
    source VARCHAR(20) DEFAULT 'sina',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_time (stock_code, trade_time),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='15分钟K线';

CREATE TABLE IF NOT EXISTS stock_kline_30min (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_time DATETIME NOT NULL,
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(20,2) DEFAULT 0,
    source VARCHAR(20) DEFAULT 'sina',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_time (stock_code, trade_time),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='30分钟K线';

CREATE TABLE IF NOT EXISTS stock_kline_60min (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_time DATETIME NOT NULL,
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    amount DECIMAL(20,2) DEFAULT 0,
    source VARCHAR(20) DEFAULT 'sina',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_time (stock_code, trade_time),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='60分钟K线';

-- stock_daily 已存在,只补充周K/月K
CREATE TABLE IF NOT EXISTS stock_kline_weekly (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    week_label VARCHAR(10) NOT NULL COMMENT '周标签 YYYY-WW',
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    source VARCHAR(20) DEFAULT 'aggregated',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_week (stock_code, week_label),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='周K线(从日K聚合)';

CREATE TABLE IF NOT EXISTS stock_kline_monthly (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    month_label VARCHAR(7) NOT NULL COMMENT '月标签 YYYY-MM',
    open_price DECIMAL(12,4) DEFAULT NULL,
    high_price DECIMAL(12,4) DEFAULT NULL,
    low_price DECIMAL(12,4) DEFAULT NULL,
    close_price DECIMAL(12,4) DEFAULT NULL,
    volume BIGINT DEFAULT 0,
    source VARCHAR(20) DEFAULT 'aggregated',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_month (stock_code, month_label),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月K线(从日K聚合)';
