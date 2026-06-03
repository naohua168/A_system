# 股票智能分析平台 — 项目架构文档

**版本：** v4.0（2026-06-01）
**数据层架构：** 市场数据→大数据层(Redis)，MySQL仅存业务数据

---

## 一、系统架构总览

### 1.1 五层架构

```
┌──────────────────────────────────────────────────────────┐
│  L5 表现层 (frontend)   Vue3 + TypeScript + ECharts      │
│  浏览器 SPA → Vite(开发) / Nginx(生产)                    │
├──────────────────────────────────────────────────────────┤
│  L4 后端服务层 (backend)  Spring Boot 3 + MyBatis-Plus   │
│  REST API → 读 Redis(市场数据) + MySQL(业务数据)           │
├──────────────────────────────────────────────────────────┤
│  L3 数据采集层 (data-collector)  Python 3.11              │
│  多源采集 → CSV → auto_seed.py(socket RESP) → Redis      │
├──────────────────────────────────────────────────────────┤
│  L2 缓存层 (Redis 7)    所有市场数据缓存                  │
│  分层 TTL: 1h(价格) / 24h(信号) / 7d(静态)               │
├──────────────────────────────────────────────────────────┤
│  L1 存储层 (MySQL 8.0)  仅业务数据                        │
│  user / watchlist / ai_chat / analysis_result             │
└──────────────────────────────────────────────────────────┘
```

### 1.2 数据流

```
[东方财富/新浪/腾讯/同花顺/通达信 API]
                     ↓
   data-collector → CSV文件 → auto_seed.py(纯socket RESP)
                     ↓
                  Redis (全量市场数据)
                     ↓
            RedisDataController (/api/v2/*)
                     ↓
               前端 ECharts 渲染

[业务数据流]
   用户操作 → 后端 → MySQL (user/watchlist/ai_chat/...)
```

### 1.3 核心原则

| 原则 | 说明 |
|:-----|:------|
| **市场数据来自 Redis** | 所有价格/K线/信号/行情数据走 `Redis → /api/v2/*` |
| **MySQL 仅存业务数据** | user / watchlist / ai_chat / analysis_result |
| **零大数据依赖** | 已移除 HDFS/Hive/Spark/YARN 全套大数据栈 |
| **纯 socket RESP** | `auto_seed.py` 和 `seed_kline.py` 不依赖任何 Redis 客户端库 |

---

## 二、表现层 (frontend)

### 2.1 技术栈

| 技术 | 版本 | 用途 |
|:-----|:-----|:------|
| Vue 3 | ^3.4 | SPA 框架 |
| TypeScript | ^5.4 | 类型安全 |
| Pinia | ^2.1 | 状态管理 |
| ECharts | ^5.5 | K 线图/云图/指标图 |
| Element Plus | ^2.7 | UI 组件库 |
| Axios | ^1.7 | HTTP 请求 |
| Vite | ^5.4 | 开发构建工具 |

### 2.2 目录结构

```
frontend/src/
├── api/                    # API 封装层
│   ├── request.ts          # Axios 实例 + 缓存拦截器 + 响应拆包
│   ├── market.ts           # 行情 API（全部 /v2/*）
│   ├── index.ts            # 指数 API（全部 /v2/*）
│   ├── signal.ts           # 信号 API（全部 /v2/*）
│   ├── info.ts             # 资讯 API（全部 /v2/*）
│   ├── analysis.ts         # 分析 API（缠论/行业排行）
│   ├── watchlist.ts        # 自选 API
│   └── user.ts             # 用户 API
├── stores/                 # Pinia 状态管理
│   ├── stock.ts            # 股票/行情状态
│   ├── signal.ts           # 信号状态
│   ├── info.ts             # 资讯状态
│   └── user.ts             # 用户状态
├── composables/            # 组合函数
│   ├── useTechnicalChart.ts    # K线图 + 技术指标渲染
│   ├── useIndicatorParams.ts   # 指标参数管理
│   ├── useStockWebSocket.ts    # WebSocket 实时行情
│   └── useApiRetry.ts          # API 重试机制
├── views/                  # 页面视图（20个）
│   ├── HomeView.vue           # 首页概览
│   ├── StockListView.vue      # 股票列表
│   ├── StockDetailView.vue    # 个股详情（K线+缠论+信号）
│   ├── IndexDetailView.vue    # 指数详情
│   ├── WatchlistView.vue      # 自选股
│   ├── ...                    # 其他页面
├── components/             # 可复用组件
│   ├── chart/                 # 图表组件
│   │   ├── TreemapChart.vue   # 行业云图
│   │   └── SectorDetailPanel.vue  # 行业概况面板（仅展示+关闭）
│   ├── common/                # 通用组件
│   │   ├── AppLayout.vue      # 布局
│   │   ├── SkeletonLoader.vue # 骨架屏
│   │   └── EmptyState.vue     # 空状态
│   └── layer/                 # 缠论组件
│       ├── LayerDetailPanel.vue
│       └── LayerSectionCard.vue
└── types/index.ts          # 全局类型定义（724行）
```

### 2.3 API 端点映射

| 前端 API 函数 | HTTP 路径 | 后端 Controller | 数据源 |
|:--------------|:----------|:----------------|:-------|
| `getStockList` | `GET /api/v2/market/list` | RedisDataController | Redis |
| `getKlineData` | `GET /api/v2/market/kline/{code}` | RedisDataController | Redis |
| `getIndexKline` | `GET /api/v2/index/{code}/kline` | RedisDataController | Redis |
| `getNorthboundLatest` | `GET /api/v2/signal/northbound/latest` | RedisDataController | Redis |
| `getChanlunAnalysis` | `GET /api/analysis/{code}/chanlun` | chanlun_server (Python) | Redis |

### 2.4 缓存策略

```typescript
// frontend/src/api/request.ts — ApiCache 内存缓存
const CACHE_RULES: [string, number][] = [
  ['/api/v2/market/list', 15000],     // 股票列表 15s
  ['/api/v2/market/industry', 30000], // 行业列表 30s
  ['/api/v2/signal', 30000],          // 信号数据 30s
  ['/api/v2/info', 30000],            // 资讯数据 30s
  ['/api/v2/analysis', 60000],        // 技术分析 60s
  ['/api/v2/index', 60000],           // 指数数据 60s
  ['/api/v2/fund', 60000],            // 基金数据 60s
]
```

---

## 三、后端服务层 (backend)

### 3.1 技术栈

| 技术 | 版本 | 用途 |
|:-----|:-----|:------|
| Spring Boot | 3.x | 应用框架 |
| MyBatis-Plus | 3.5.x | ORM |
| Redis | 7.x | 缓存层 |
| MySQL | 8.0 | 持久化 |

### 3.2 三层架构

```
Controller (@RestController)  ← 10 个活跃 Controller
   └─ Service (@Service)      ← 活跃 Service
       └─ Mapper (@Mapper)    ← MyBatis Mapper
           └─ XML             ← SQL 映射
```

### 3.3 活跃 Controller 清单

| Controller | 路由前缀 | 数据源 | 说明 |
|:-----------|:---------|:-------|:-----|
| `RedisDataController` | `/api/v2` | Redis | **主数据源** — 行情/指数/信号/资讯/基金 |
| `AnalysisController` | `/api/v2/analysis` | MySQL | 年/月收益率、技术分析 |
| `SignalDataController` | `/api/v2/signal` | MySQL+Redis | 龙虎榜/北向/行业排行 |
| `InfoController` | `/api/v2/info` | MySQL | 研报/新闻/公告 |
| `FundController` | `/api/v2/fund` | MySQL | 基金信息/净值/持仓 |
| `UserController` | `/api/v2/user` | MySQL | 用户管理 |
| `WatchlistController` | `/api/v2/watchlist` | MySQL | 自选股管理 |
| `AiDialogueController` | `/api/v2/ai` | MySQL | AI 对话 |
| `CacheController` | `/api/cache` | Redis | 缓存清理 |
| `RedisDataController` | `/api/v2` | Redis | **市场数据主入口** |

### 3.4 Redis Key 设计

| Redis Key | 数据 | TTL | 写入源 |
|:----------|:-----|:----|:-------|
| `market:stock_basic` | 全量股票实时行情(price/changePct…) | 1h | auto_seed.py |
| `market:kline_{code}` | 个股日K线(121条) | 12h | seed_kline.py |
| `market:index_kline_{code}` | 指数日K线 | 24h | seed_kline.py |
| `market:sector_kline_{industry}` | 板块K线 | 12h | write_kline_to_redis.py |
| `market:northbound` | 北向资金 | 24h | auto_seed.py |
| `market:hot_reason` | 热点题材 | 24h | auto_seed.py |
| `market:industry_compare` | 行业排行 | 24h | auto_seed.py |
| `market:max_date` | 最新交易日 | 1h | auto_seed.py |
| `market:cls_news` | 财联社快讯 | 24h | auto_seed.py |
| `market:global_news` | 全球资讯 | 24h | auto_seed.py |
| `market:index_list` | 指数列表 | 7d | auto_seed.py |

---

## 四、数据采集层 (data-collector)

### 4.1 技术栈

| 组件 | 版本 | 用途 |
|:-----|:-----|:------|
| Python | 3.11 | 采集脚本 |
| urllib + socket | stdlib | HTTP 请求 + Redis 写入（零外部依赖） |
| ThreadPoolExecutor | stdlib | 并发K线采集 |

### 4.2 核心文件

| 文件 | 功能 |
|:-----|:------|
| `auto_seed.py` | **自愈管道** — 从 CSV 写入实时行情/信号到 Redis（纯 socket RESP） |
| `seed_kline.py` | **K线 seed** — 从腾讯API获取K线写入Redis（多线程，零外部依赖） |
| `write_kline_to_redis.py` | **CSV→Redis K线** — 供 scheduler 定期调用 |
| `scheduler/run_collector.py` | **统一调度器** — PID 1 长期运行，循环采集全市场数据 |
| `scheduler/sync_engine.py` | **同步引擎** — 基于 DataCatalog 的数据同步 |
| `config.py` | 全局配置 |
| `collectors/` | 多源采集器（东方财富/新浪/腾讯/同花顺/通达信） |
| `pipeline/` | 采集管道（CollectionPipeline / Orchestrator） |
| `storage/` | 存储管理器（CSV + MySQL 双后端） |
| `adapters/` | 适配器层（统一数据源协议） |

### 4.3 数据更新策略 (TTL 三层)

| 层级 | TTL | 数据 | 刷新方式 |
|:-----|:----|:-----|:---------|
| **价格高频** | **1h** | stock_basic(price/changePct), kline_* | 每次 auto_seed 强制覆盖 |
| **动态信号** | **24h** | northbound, hot_reason, cls_news | TTL>600 跳过，过期更新 |
| **静态基础** | **7d** | index_list, fund_list | 首写后几乎不变 |

---

## 五、数据库设计 (MySQL 8.0)

### 5.1 数据库总览

**数据库名：** `stock_analysis`（utf8mb4）
**数据流：** 仅存储业务数据，市场数据走 Redis

### 5.2 表清单（28 张表）

| 类别 | 表名 | 用途 | 数据量预估 |
|:-----|:-----|:-----|:-----------|
| **用户** | `user` | 用户账号/权限 | 小 |
| **自选** | `watchlist` | 用户自选股票/基金 | 小 |
| **对话** | `ai_chat` | AI 对话历史 | 中 |
| **分析** | `analysis_result` | 技术分析/缠论结果缓存 | 中 |
| **预计算** | `precomputed_result` | 预计算指标 | 中 |
| **股票** | `stock` | 股票基础信息 | 5,542 行 |
| **日K线** | `stock_daily` | 股票日K线 | 125 万行/年 |
| **指数** | `market_index` | 指数标识符 | 15 行 |
| **指数K线** | `index_daily` | 指数日K线 | 中 |
| **基金** | `fund` | 基金基础信息 | 中 |
| **基金净值** | `fund_nav` | 基金净值历史 | 中 |
| **基金持仓** | `fund_holding` | 基金持仓明细 | 中 |
| **热点题材** | `signal_hot_reason` | 同花顺热点归因 | 中 |
| **龙虎榜** | `signal_dragon_tiger` | 龙虎榜汇总 | 中 |
| **龙虎榜明细** | `signal_dragon_tiger_detail` | 龙虎榜买卖席明细 | 中 |
| **北向资金** | `signal_northbound` | 北向资金分钟级 | 中 |
| **限售解禁** | `signal_lockup` | 解禁日历 | 中 |
| **限售解禁明细** | `signal_lockup_detail` | 解禁明细 | 中 |
| **行业排行** | `signal_daily_industry` | 行业涨跌排行 | 中 |
| **概念板块** | `signal_concept_block` | 百度概念板块 | 中 |
| **资金流向** | `signal_fund_flow` | 个股资金流向 | 中 |
| **财联社快讯** | `info_cls_news` | 财联社新闻 | 中 |
| **全球资讯** | `info_global_news` | 全球财经资讯 | 中 |
| **个股新闻** | `info_stock_news` | 个股新闻 | 中 |
| **研报** | `info_research_report` | 券商研报 | 中 |
| **一致预期** | `info_consensus_eps` | 机构EPS预测 | 中 |
| **公告** | `info_filing` | 巨潮公告 | 中 |
| **研报PDF** | `info_report_pdf` | 研报PDF元数据 | 小 |

### 5.3 核心表设计

#### 5.3.1 `user` — 用户表

```sql
CREATE TABLE `user` (
    `id`                    BIGINT          AUTO_INCREMENT  COMMENT '用户ID',
    `username`              VARCHAR(50)     NOT NULL        COMMENT '用户名',
    `password`              VARCHAR(255)    NOT NULL        COMMENT '密码（加密）',
    `email`                 VARCHAR(100)    DEFAULT NULL    COMMENT '邮箱',
    `phone`                 VARCHAR(20)     DEFAULT NULL    COMMENT '手机号',
    `avatar`                VARCHAR(500)    DEFAULT NULL    COMMENT '头像URL',
    `role`                  TINYINT         DEFAULT 0       COMMENT '角色: 0=USER, 1=PREMIUM, 2=ADMIN, 3=SUPER_ADMIN',
    `status`                TINYINT         DEFAULT 0       COMMENT '状态: 0=正常, 1=禁用',
    `last_login_at`         DATETIME        DEFAULT NULL    COMMENT '最后登录',
    `created_at`            DATETIME        DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

#### 5.3.2 `stock` — 股票基础信息

```sql
CREATE TABLE `stock` (
    `id`                BIGINT          AUTO_INCREMENT,
    `stock_code`        VARCHAR(10)     NOT NULL        COMMENT '股票代码',
    `stock_name`        VARCHAR(50)     NOT NULL        COMMENT '股票名称',
    `market`            VARCHAR(10)     DEFAULT NULL    COMMENT '市场: SH/SZ/BJ',
    `industry`          VARCHAR(50)     DEFAULT NULL    COMMENT '所属行业',
    `listing_date`      DATE            DEFAULT NULL    COMMENT '上市日期',
    `total_shares`      DECIMAL(20,2)   DEFAULT NULL    COMMENT '总股本',
    `circulated_shares` DECIMAL(20,2)   DEFAULT NULL    COMMENT '流通股本',
    `pe`                DECIMAL(10,2)   DEFAULT NULL    COMMENT '市盈率',
    `pb`                DECIMAL(10,2)   DEFAULT NULL    COMMENT '市净率',
    `total_market_cap`  DECIMAL(20,2)   DEFAULT NULL    COMMENT '总市值',
    `status`            TINYINT         DEFAULT 1       COMMENT '0=退市, 1=正常',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_code` (`stock_code`),
    KEY `idx_industry` (`industry`),
    KEY `idx_market` (`market`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基础信息表';
```

#### 5.3.3 `stock_daily` — 股票日K线

```sql
CREATE TABLE `stock_daily` (
    `id`              BIGINT          AUTO_INCREMENT,
    `stock_code`      VARCHAR(10)     NOT NULL        COMMENT '股票代码',
    `trade_date`      DATE            NOT NULL        COMMENT '交易日期',
    `open_price`      DECIMAL(10,2)   DEFAULT NULL    COMMENT '开盘价',
    `high_price`      DECIMAL(10,2)   DEFAULT NULL    COMMENT '最高价',
    `low_price`       DECIMAL(10,2)   DEFAULT NULL    COMMENT '最低价',
    `close_price`     DECIMAL(10,2)   DEFAULT NULL    COMMENT '收盘价',
    `pre_close`       DECIMAL(10,2)   DEFAULT NULL    COMMENT '昨收价',
    `volume`          BIGINT          DEFAULT NULL    COMMENT '成交量（股）',
    `amount`          DECIMAL(20,2)   DEFAULT NULL    COMMENT '成交额（元）',
    `change_percent`  DECIMAL(10,4)   DEFAULT NULL    COMMENT '涨跌幅(%)',
    `turnover_rate`   DECIMAL(10,4)   DEFAULT NULL    COMMENT '换手率(%)',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_date` (`stock_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_stock_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日K线数据表';
```

#### 5.3.4 `watchlist` — 自选表

```sql
CREATE TABLE `watchlist` (
    `id`          BIGINT          AUTO_INCREMENT,
    `user_id`     BIGINT          NOT NULL        COMMENT '用户ID',
    `asset_type`  TINYINT         NOT NULL        COMMENT '类型: 0=股票, 1=基金',
    `asset_code`  VARCHAR(10)     NOT NULL        COMMENT '资产代码',
    `remark`      VARCHAR(200)    DEFAULT NULL    COMMENT '备注',
    `sort_order`  INT             DEFAULT 0       COMMENT '排序',
    `created_at`  DATETIME        DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_asset` (`user_id`, `asset_type`, `asset_code`),
    KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选表';
```

#### 5.3.5 `ai_chat` — AI 对话记录

```sql
CREATE TABLE `ai_chat` (
    `id`          BIGINT          AUTO_INCREMENT,
    `user_id`     BIGINT          NOT NULL        COMMENT '用户ID',
    `session_id`  VARCHAR(50)     NOT NULL        COMMENT '会话ID',
    `role`        TINYINT         NOT NULL        COMMENT '0=用户, 1=AI',
    `content`     TEXT            NOT NULL        COMMENT '对话内容',
    `asset_code`  VARCHAR(10)     DEFAULT NULL    COMMENT '关联资产代码',
    `created_at`  DATETIME        DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_session` (`session_id`),
    KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI对话记录表';
```

#### 5.3.6 `signal_dragon_tiger` — 龙虎榜

```sql
CREATE TABLE `signal_dragon_tiger` (
    `id`            BIGINT          AUTO_INCREMENT,
    `trade_date`    DATE            NOT NULL        COMMENT '交易日期',
    `stock_code`    VARCHAR(10)     NOT NULL        COMMENT '股票代码',
    `stock_name`    VARCHAR(50)     DEFAULT NULL    COMMENT '股票名称',
    `reason`        VARCHAR(200)    DEFAULT NULL    COMMENT '上榜原因',
    `net_buy_wan`   DECIMAL(20,2)   DEFAULT NULL    COMMENT '净买额(万)',
    `buy_wan`       DECIMAL(20,2)   DEFAULT NULL    COMMENT '买入额(万)',
    `sell_wan`      DECIMAL(20,2)   DEFAULT NULL    COMMENT '卖出额(万)',
    `change_pct`    DECIMAL(10,4)   DEFAULT NULL    COMMENT '涨跌幅%',
    `turnover_pct`  DECIMAL(10,4)   DEFAULT NULL    COMMENT '换手率%',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_code` (`trade_date`, `stock_code`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜数据表';
```

#### 5.3.7 `signal_northbound` — 北向资金

```sql
CREATE TABLE `signal_northbound` (
    `id`           BIGINT          AUTO_INCREMENT,
    `trade_date`   VARCHAR(10)     NOT NULL        COMMENT '交易日期',
    `time`         VARCHAR(10)     DEFAULT NULL    COMMENT '分钟时间 HH:MM',
    `hgt_yi`       DECIMAL(20,4)   DEFAULT NULL    COMMENT '沪股通净流入(亿)',
    `sgt_yi`       DECIMAL(20,4)   DEFAULT NULL    COMMENT '深股通净流入(亿)',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_time` (`trade_date`, `time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='北向资金数据表';
```

### 5.4 主外键关联

| 父表 | 子表 | 关联字段 | 说明 |
|:-----|:-----|:---------|:-----|
| `user` (id) | `watchlist` (user_id) | 外键逻辑 | 用户→自选 |
| `user` (id) | `ai_chat` (user_id) | 外键逻辑 | 用户→对话 |
| `stock` (stock_code) | `stock_daily` (stock_code) | 业务键 | 股票→日K线 |
| `stock` (stock_code) | `signal_*` (stock_code) | 业务键 | 股票→信号 |
| `fund` (fund_code) | `fund_nav` (fund_code) | 业务键 | 基金→净值 |
| `fund` (fund_code) | `fund_holding` (fund_code) | 业务键 | 基金→持仓 |

> **注意：** 除 `watchlist.user_id` → `user.id` 有强外键约束外，其余关联通过业务代码维护（`stock_code` / `fund_code` 字段），MySQL 层面未设置外键约束，以保证写入性能和数据采集灵活性。

### 5.5 索引策略

| 表 | 索引 | 类型 | 说明 |
|:---|:-----|:-----|:-----|
| `user` | `uk_username`, `uk_email` | 唯一 | 登录查询 |
| `stock` | `uk_stock_code` | 唯一 | 代码查询 |
| `stock` | `idx_industry` | B-tree | 行业筛选 |
| `stock_daily` | `uk_stock_date` | 唯一联合 | K线去重 |
| `stock_daily` | `idx_trade_date` | B-tree | 日期范围查询 |
| `stock_daily` | `idx_stock_code` | B-tree | 股票代码查询 |
| `fund_nav` | `uk_fund_date` | 唯一联合 | 净值去重 |
| `watchlist` | `uk_user_asset` | 唯一联合 | 防止重复添加 |
| `signal_dragon_tiger` | `uk_date_code` | 唯一联合 | 日级别去重 |
| `signal_northbound` | `uk_date_time` | 唯一联合 | 分钟级去重 |
| `ai_chat` | `idx_session` | B-tree | 会话查询 |
| `info_*` | `idx_stock_code` | B-tree | 资讯按代码查询 |

---

## 六、Docker 部署

### 6.1 服务组成

| 服务 | 镜像 | 端口 | 内存限制 | 说明 |
|:-----|:-----|:-----|:---------|:-----|
| `mysql` | mysql:8.0 | 3307→3306 | 2G | 业务数据库 |
| `redis` | redis:7-alpine | 6379 | 512M | 缓存层 |
| `backend` | spring boot | 8082 | 1G | REST API |
| `frontend` | nginx:1.25 | 80 | 256M | 静态文件 |
| `ai-service` | fastapi | 8000 | 2G | AI 对话 |

### 6.2 启动命令

```bash
# 开发环境（本地 Vite + Docker 后端）
docker compose up -d mysql redis backend

# 生产环境
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

> **注意：** 大数据层（HDFS/Hive/Spark/YARN/Prometheus/Grafana）已在 v4.0 中移除。如需监控请自行添加。

### 6.3 网络架构

```
app-net (172.x.0.0/16)
├── mysql:3306
├── redis:6379
├── backend:8082
├── frontend:80
├── ai-service:8000
└── [collector-net 桥接]
    └── data-collector (通过 app-net 访问 Redis)
```

---

## 七、清理记录 (v4.0)

### 7.1 后端删除

| 文件 | 原因 |
|:-----|:------|
| `MarketController.java` | 已废弃，前端已切换到 RedisDataController |
| `IndexController.java` | 已废弃，前端已切换到 RedisDataController |
| `RedisMarketService.java` | 未引用，功能内联到 RedisDataController |
| `RedisCacheService.java` | 未引用，Hive 不可用 |
| `StockService.java` + impl | 仅被废弃 MarketController 引用 |
| `StockDailyService.java` + impl | 仅被废弃 MarketController 引用 |
| `IndexService.java` + impl | 仅被废弃 IndexController 引用 |
| `HiveDataSourceConfig.java` | 空壳类 |
| `StockMapper.java` + xml | 仅被废弃代码引用 |
| `MarketIndexMapper.java` | 仅被废弃代码引用 |

### 7.2 采集层删除

| 文件 | 原因 |
|:-----|:------|
| `hive_to_redis.py` | 依赖不可用 pyhive |
| `load_hive.py`, `upload_hdfs.py` | 依赖不可用 HDFS |
| `scheduler/upload_to_hdfs.py` | 依赖不可用 HDFS |
| `scheduler/restore_from_hdfs.py` | 依赖不可用 Hive |
| `scheduler/run_with_hdfs.py` | HDFS 双写管道废弃 |
| `deploy_new_data.py`, `fix_all_data.py` | 依赖不可用 pyhive |
| `collect_full_market.py`, `astock_collector.py` | 依赖 HDFS/Hive |
| `force_real_data.py`, `recover_from_csv.py` | 被 auto_seed 替代 |
| `collect_kline.py`, `batch_fetch_all_kline.py` | 被 seed_kline 替代 |
| `sector_kline_calc.py` | 被 write_kline_to_redis 替代 |
| `scheduler/aggregate_kline.py` | MySQL 版聚合废弃 |
| `scheduler/kline_master.py` | 已被 run_collector 替代 |
| 15 个 debug/temp/check 脚本 | 一次性调试用途 |

### 7.3 Docker 移除

| 服务 | 原因 |
|:-----|:------|
| namenode + 2x datanode | HDFS 未使用，~5G 内存 |
| resourcemanager + nodemanager | YARN 未使用，~3G |
| hive-server | Hive 未使用，~2G |
| spark-master + spark-worker | Spark 未使用，~5G |
| prometheus + grafana | 监控未启用 |

### 7.4 前端删除

| 文件 | 原因 |
|:-----|:------|
| `AiChatPanel.vue` | 未引用 |
| `AiSignalSummary.vue` | 未引用 |
| `LayerStatusBadge.vue` | 未引用 |
| `analysis.ts` 6个未用函数 | 未被任何视图调用 |
