-- ============================================================
-- 信号层扩展表 DDL — JSON-only 数据类型迁移到 MySQL
-- 新增: concept_block / fund_flow / dragon_tiger_detail / lockup_detail
-- ============================================================

-- 1. 概念板块归属
DROP TABLE IF EXISTS signal_concept_block;
CREATE TABLE signal_concept_block (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    block_type       VARCHAR(20)    NOT NULL COMMENT '板块类型: industry/concept/region/concept_tag',
    block_name       VARCHAR(100)   NOT NULL COMMENT '板块名称',
    change_pct       VARCHAR(20)    DEFAULT NULL COMMENT '涨跌幅',
    description      VARCHAR(500)   DEFAULT NULL COMMENT '描述',
    source           VARCHAR(50)    DEFAULT 'baidu' COMMENT '数据来源',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_stock_code (stock_code),
    INDEX idx_block_type (block_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='信号层-概念板块归属(百度PAE)';

-- 2. 个股资金流向日级历史
DROP TABLE IF EXISTS signal_fund_flow;
CREATE TABLE signal_fund_flow (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    trade_date       VARCHAR(10)    DEFAULT NULL COMMENT '交易日期',
    close            DECIMAL(10,2)  DEFAULT NULL COMMENT '收盘价',
    change_pct       VARCHAR(20)    DEFAULT NULL COMMENT '涨跌幅',
    super_net_in     VARCHAR(50)    DEFAULT NULL COMMENT '超大单净流入',
    large_net_in     VARCHAR(50)    DEFAULT NULL COMMENT '大单净流入',
    medium_net_in    VARCHAR(50)    DEFAULT NULL COMMENT '中单净流入',
    little_net_in    VARCHAR(50)    DEFAULT NULL COMMENT '小单净流入',
    main_in          VARCHAR(50)    DEFAULT NULL COMMENT '主力净流入',
    source           VARCHAR(50)    DEFAULT 'baidu' COMMENT '数据来源',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_stock_code (stock_code),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='信号层-个股资金流向(百度)';

-- 3. 全市场龙虎榜明细
DROP TABLE IF EXISTS signal_dragon_tiger_detail;
CREATE TABLE signal_dragon_tiger_detail (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    trade_date       VARCHAR(10)    NOT NULL COMMENT '交易日期',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    stock_name       VARCHAR(50)    DEFAULT NULL COMMENT '股票名称',
    reason           VARCHAR(500)   DEFAULT NULL COMMENT '上榜原因',
    close            DECIMAL(10,2)  DEFAULT NULL COMMENT '收盘价',
    change_pct       DECIMAL(10,2)  DEFAULT NULL COMMENT '涨跌幅',
    net_buy_wan      DECIMAL(15,2)  DEFAULT NULL COMMENT '净买入额(万元)',
    buy_wan          DECIMAL(15,2)  DEFAULT NULL COMMENT '买入额(万元)',
    sell_wan         DECIMAL(15,2)  DEFAULT NULL COMMENT '卖出额(万元)',
    turnover_pct     DECIMAL(10,2)  DEFAULT NULL COMMENT '换手率',
    source           VARCHAR(50)    DEFAULT 'akshare' COMMENT '数据来源',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_trade_date (trade_date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_net_buy (net_buy_wan)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='信号层-龙虎榜明细(东财DC)';

-- 4. 限售解禁明细
DROP TABLE IF EXISTS signal_lockup_detail;
CREATE TABLE signal_lockup_detail (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    lockup_date      VARCHAR(10)    DEFAULT NULL COMMENT '解禁日期',
    lockup_type      VARCHAR(100)   DEFAULT NULL COMMENT '限售股类型',
    shares           DECIMAL(20,2)  DEFAULT NULL COMMENT '解禁数量',
    float_ratio      VARCHAR(20)    DEFAULT NULL COMMENT '占流通股比例',
    ratio            VARCHAR(20)    DEFAULT NULL COMMENT '占总市值比例',
    type_tag         VARCHAR(20)    DEFAULT 'history' COMMENT '历史/将来: history/upcoming',
    source           VARCHAR(50)    DEFAULT 'akshare' COMMENT '数据来源',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_stock_code (stock_code),
    INDEX idx_type_tag (type_tag),
    INDEX idx_lockup_date (lockup_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='信号层-限售解禁明细(akshare)';
