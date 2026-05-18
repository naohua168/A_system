-- ============================================================
-- 资讯层 DDL — 研报 + 新闻 + 公告 统一 MySQL 建表脚本
-- 从 a-stock-data 项目的研报层、新闻层、公告层迁移合并
-- ============================================================

-- 1. 研报记录
CREATE TABLE IF NOT EXISTS info_research_report (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    title            VARCHAR(500)   NOT NULL COMMENT '研报标题',
    publish_date     VARCHAR(8)     DEFAULT NULL COMMENT '发布日期 YYYYMMDD',
    org_name         VARCHAR(100)   DEFAULT NULL COMMENT '机构名称',
    rating           VARCHAR(50)    DEFAULT NULL COMMENT '评级(买入/增持等)',
    predict_eps_this_year DECIMAL(10,4) DEFAULT NULL COMMENT '当年预测EPS',
    predict_eps_next_year DECIMAL(10,4) DEFAULT NULL COMMENT '次年预测EPS',
    info_code        VARCHAR(100)   DEFAULT NULL COMMENT 'PDF下载标识',
    page_url         VARCHAR(500)   DEFAULT NULL COMMENT '研报页面URL',
    source           VARCHAR(50)    DEFAULT 'information' COMMENT '数据来源',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_stock_code (stock_code),
    INDEX idx_publish_date (publish_date),
    INDEX idx_org_name (org_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-研报记录(东财reportapi)';

-- 2. 一致预期EPS
CREATE TABLE IF NOT EXISTS info_consensus_eps (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    year             VARCHAR(4)     NOT NULL COMMENT '预测年度',
    forecast_count   INT            DEFAULT 0 COMMENT '预测机构数',
    min_eps          DECIMAL(10,4)  DEFAULT NULL COMMENT '最小值',
    avg_eps          DECIMAL(10,4)  DEFAULT NULL COMMENT '均值',
    max_eps          DECIMAL(10,4)  DEFAULT NULL COMMENT '最大值',
    industry_avg     DECIMAL(10,4)  DEFAULT NULL COMMENT '行业平均数',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_stock_year (stock_code, year),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-机构一致预期EPS(同花顺源)';

-- 3. 个股新闻
CREATE TABLE IF NOT EXISTS info_stock_news (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    title            VARCHAR(500)   NOT NULL COMMENT '新闻标题',
    publish_time     VARCHAR(20)    DEFAULT NULL COMMENT '发布时间 YYYY-MM-DD HH:MM:SS',
    content_summary  VARCHAR(500)   DEFAULT NULL COMMENT '内容摘要',
    source           VARCHAR(100)   DEFAULT '东方财富' COMMENT '来源',
    url              VARCHAR(500)   DEFAULT NULL COMMENT '链接',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_stock_code (stock_code),
    INDEX idx_publish_time (publish_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-个股新闻(东财源)';

-- 4. 财联社快讯
CREATE TABLE IF NOT EXISTS info_cls_news (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    title            VARCHAR(500)   NOT NULL COMMENT '快讯标题',
    publish_time     VARCHAR(20)    DEFAULT NULL COMMENT '发布时间 YYYY-MM-DD HH:MM:SS',
    content          TEXT           COMMENT '快讯内容',
    source           VARCHAR(100)   DEFAULT '财联社' COMMENT '来源',
    url              VARCHAR(500)   DEFAULT NULL COMMENT '链接',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_publish_time (publish_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-财联社快讯(分钟级电报)';

-- 5. 全球财经资讯
CREATE TABLE IF NOT EXISTS info_global_news (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    title            VARCHAR(500)   NOT NULL COMMENT '资讯标题',
    publish_time     VARCHAR(20)    DEFAULT NULL COMMENT '发布时间 YYYY-MM-DD HH:MM:SS',
    summary          VARCHAR(500)   DEFAULT NULL COMMENT '摘要',
    source           VARCHAR(100)   DEFAULT '东方财富' COMMENT '来源',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_publish_time (publish_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-全球财经资讯(东财源)';

-- 6. 巨潮公告
CREATE TABLE IF NOT EXISTS info_filing (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    title            VARCHAR(500)   NOT NULL COMMENT '公告标题',
    publish_date     VARCHAR(8)     DEFAULT NULL COMMENT '发布日期 YYYYMMDD',
    filing_type      VARCHAR(100)   DEFAULT '公告' COMMENT '公告类别',
    market           VARCHAR(10)    DEFAULT NULL COMMENT '市场(沪市/深市/北交所)',
    content_summary  VARCHAR(500)   DEFAULT NULL COMMENT '内容摘要',
    url              VARCHAR(500)   DEFAULT NULL COMMENT '链接',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_stock_code (stock_code),
    INDEX idx_publish_date (publish_date),
    INDEX idx_filing_type (filing_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-巨潮公告';

-- 7. 研报PDF下载记录
CREATE TABLE IF NOT EXISTS info_report_pdf (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    report_id        BIGINT         NOT NULL COMMENT '关联研报ID(info_research_report.id)',
    stock_code       VARCHAR(10)    NOT NULL COMMENT '股票代码',
    title            VARCHAR(500)   DEFAULT NULL COMMENT '研报标题',
    pdf_path         VARCHAR(500)   NOT NULL COMMENT 'PDF文件路径',
    file_size        BIGINT         DEFAULT 0 COMMENT '文件大小(字节)',
    created_at       DATETIME       DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_report_id (report_id),
    INDEX idx_stock_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资讯层-研报PDF下载记录';
