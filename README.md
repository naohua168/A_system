# 基金股票智能分析系统 (v4.1)

轻量级金融数据分析平台，覆盖 **数据采集 → Redis 缓存 → 后端 API → 前端展示** 全链路。
采用 **CSV→Redis 直写管道** 实现零外部依赖，已剔除全部 Hadoop/Hive/Spark/Kafka 等大数据组件。

> **当前版本**: v4.1 (2026-06-03)
> - ✅ **数据采集层** — 腾讯 API 直取实时行情 + K 线 + 信号数据，RESP 协议直写 Redis
> - ✅ **后端 API** — 10+ Controller, 40+ 端点, Redis 直读 + MyBatis MySQL
> - ✅ **前端** — 33 视图页面, ECharts K 线/缠论/技术指标, Element Plus UI
> - ✅ **AI 服务** — FastAPI + 多智能体对话 (可选)
> - ✅ **缠论分析** — Python bridge + Redis K 线，个股/指数自动检测

---

## 目录

- [1. 架构总览](#1-架构总览)
- [2. 数据流](#2-数据流)
- [3. 技术栈](#3-技术栈)
- [4. 项目结构](#4-项目结构)
- [5. 目录与文件详解](#5-目录与文件详解)
- [6. API 端点](#6-api-端点)
- [7. Redis Key 设计](#7-redis-key-设计)
- [8. 数据库设计](#8-数据库设计)
- [9. 部署](#9-部署)
- [10. 开发指南](#10-开发指南)
- [11. 运行验证](#11-运行验证)
- [12. 变更日志](#12-变更日志)

---

## 1. 架构总览

```
┌────────────────────────────────────────────────────────────┐
│                     用户 (浏览器)                            │
└────────────────────────┬───────────────────────────────────┘
                         │ HTTP
                         ▼
┌────────────────────────────────────────────────────────────┐
│  Docker 网络 (bigdata-net)                                   │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Frontend  │  │  Backend   │  │   Redis   │  │  MySQL   │ │
│  │ (Vite :80) │  │(Java :8082)│  │(:6379)    │  │(:3306)   │ │
│  └───────────┘  └─────┬─────┘  └──────────┘  └──────────┘ │
│                        │                                     │
│               ┌────────┴────────┐                            │
│               │  data-collector  │                            │
│               │  (Python 容器)    │                            │
│               │  CSV → Redis     │                            │
│               └─────────────────┘                             │
│                                                               │
│  AI Service (FastAPI :8000) — 可选，Docker 外运行             │
└─────────────────────────────────────────────────────────────┘
```

### 容器清单 (4 个活跃)

| 服务 | 容器名 | 镜像 | 端口 | 功能 |
|:-----|:-------|:-----|:----:|:-----|
| **Backend** | `backend` | `stock-backend:fixed2` | 8082 | REST API (Redis 直读) |
| **Redis** | `redis` | `redis:7-alpine` | 6379 | 缓存 (主数据源) |
| **MySQL** | `mysql` | `mysql:8.0` | 3306 | 业务数据 (用户/自选/资讯) |
| **Data Collector** | `data-collector` | `stock-data-collector:latest` | — | 数据采集 (auto_seed) |

### 逻辑分层 (4 层)

| 层 | 模块 | 职责 |
|:---|:-----|:------|
| **L1 采集层** | `data-collector/` | 腾讯财经 API → CSV → Redis (RESP 直写) |
| **L2 服务层** | `backend/` | Spring Boot REST API, Redis 直读缓存, MySQL 存业务 |
| **L3 展示层** | `frontend/` | Vue 3 SPA, ECharts K 线/缠论/技术指标 |
| **L4 AI 层** | `ai-service/` | FastAPI 多智能体对话 (可选，本地开发) |

### 已移除服务 (v4.x)

| 服务 | 移除版本 | 说明 |
|:-----|:---------|:------|
| Hadoop (NameNode/DataNode) | v4.0 | 大数据组件全部移除 |
| Hive / Spark | v4.0 | 数据湖不再需要 |
| Kafka / Zookeeper | v4.0 | 消息队列移除 |
| Prometheus / Grafana | v4.1 | 监控栈移除，简化部署 |

---

## 2. 数据流

### 实时数据

```
腾讯财经 API (HTTP, 每批 100 只, 20 并发)
    │
    ▼
auto_seed.py (Python 原生 socket RESP 协议, 零外部依赖)
    │
    ├──→ market:kline_{code}        (个股 K 线, TTL=12h)
    ├──→ market:index_kline_{code}   (指数 K 线, TTL=24h)
    ├──→ market:stock_basic          (5542 只实时行情, TTL=1h)
    ├──→ market:index_list           (5 只指数, K 线修正, TTL=1h)
    ├──→ market:sector_ranking       (行业涨跌排行, TTL=1h)
    ├──→ market:stats                (涨跌统计, TTL=1h)
    ├──→ market:northbound           (北向资金最后 50 条, TTL=1h)
    ├──→ market:hot_reason           (题材热点, TTL=1h)
    ├──→ market:dragon_tiger         (龙虎榜, TTL=1h)
    ├──→ market:industry_treemap     (行业云图 99 个, TTL=1h)
    └──→ market:industry_compare     (行业对比, TTL=1h)
            │
            ▼
Backend (RedisDataController 直读 Redis, 无 MySQL 中间层)
            │
            ▼
Frontend (Vue 3 + ECharts)
```

### 关键设计

- **零外部依赖**: `auto_seed.py` 仅用 `urllib` + 原生 `socket` (RESP 协议)，无需 `redis-py` / `pandas` / `akshare`
- **三级 TTL 策略**: 价格数据 1h / 信号数据 1h / 静态数据 24h+
- **K 线修正**: 写入指数列表后自动用 K 线收盘价覆盖 CSV 滞后数据
- **多数据源融合**: 行业云图融合申万行业 + 东方财富板块，去重合并
- **交易时段感知**: 交易时段 1 分钟刷新，非交易时段 30 分钟

---

## 3. 技术栈

| 组件 | 技术 | 版本 |
|:-----|:-----|:----:|
| **后端** | Java / Spring Boot / MyBatis-Plus / Spring Security | JDK 17 / 2.7 |
| **前端** | Vue 3 / TypeScript / ECharts 5 / Element Plus | 3.4 |
| **缓存** | Redis (RESP 协议直写) | 7-alpine |
| **数据库** | MySQL (仅用户/自选/资讯) | 8.0 |
| **采集器** | Python 原生 socket + urllib | 3.11 |
| **AI 服务** | Python FastAPI + SiliconFlow API (可选) | FastAPI |
| **部署** | Docker Compose | v2.23+ |
| **代码量** | ~450 文件, ~65K 行 | |

---

## 4. 项目结构

```
f:/bs/A_system/
├── data-collector/          # L1: 数据采集层
│   ├── auto_seed.py          # 核心管道: CSV→Redis (socket RESP 零依赖)
│   ├── seed_kline.py         # K 线采集: 腾讯 API → Redis (5542 只)
│   ├── write_kline_to_redis.py  # CSV→Redis K 线写入
│   ├── hdfs_upload.py        # HDFS 上传 (可选)
│   ├── hdfs_to_redis.py      # HDFS→Redis 同步
│   ├── collectors/           # 采集器模块
│   │   ├── tencent_collector.py   # 腾讯行情采集
│   │   └── ...
│   └── scheduler/
│       ├── run_collector.py  # 主调度器 (PID 1)
│       └── sync_to_mysql.py  # CSV→MySQL 同步
│
├── backend/                  # L2: 后端 API 服务
│   ├── src/main/java/com/stock/
│   │   ├── controller/       # REST Controller
│   │   │   ├── RedisDataController.java   # 市场/指数/K 线 (Redis 直读)
│   │   │   ├── AnalysisController.java    # 缠论/量化分析
│   │   │   ├── SignalDataController.java  # 信号数据
│   │   │   ├── InfoController.java        # 资讯
│   │   │   ├── UserController.java        # 用户/登录
│   │   │   ├── FundController.java        # 基金
│   │   │   └── ...                        # 10+ 个 Controller
│   │   ├── service/          # 业务逻辑层
│   │   ├── mapper/           # MyBatis Mapper
│   │   └── entity/           # 数据实体
│   ├── src/main/resources/
│   │   ├── application.yml   # 主配置 (双 profile: dev/prod)
│   │   └── mapper/           # MyBatis XML Mapper
│   └── pom.xml
│
├── frontend/                 # L3: 前端 SPA
│   ├── src/
│   │   ├── api/              # API 封装 (axios, 20 个模块)
│   │   │   ├── request.ts    # 请求/响应拦截器 (JWT + 缓存)
│   │   │   ├── market.ts     # 市场数据 API
│   │   │   ├── index.ts      # 指数 API
│   │   │   ├── info.ts       # 资讯 API
│   │   │   └── ...
│   │   ├── views/            # 33 个视图页面
│   │   │   ├── HomeView.vue          # 首页大盘
│   │   │   ├── StockDetailView.vue   # 个股详情 (K 线+缠论)
│   │   │   ├── LoginView.vue         # 登录
│   │   │   ├── NewsView.vue          # 资讯
│   │   │   └── ...
│   │   ├── components/       # 可复用组件
│   │   │   ├── chart/        # 图表组件 (K 线/云图/排行)
│   │   │   │   ├── KLineChart.vue    # K 线主图
│   │   │   │   ├── useTechnicalChart.ts  # 缠论+技术指标渲染
│   │   │   │   └── ...
│   │   │   └── common/       # 通用组件 (EmptyState/SkeletonLoader)
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── composables/      # 组合函数
│   │   └── utils/            # 工具函数
│   ├── nginx.prod.conf       # Nginx 生产配置
│   └── package.json
│
├── ai-service/               # L4: AI 服务 (可选)
│   ├── app/
│   │   ├── agents/           # 7 个 AI Agent
│   │   │   ├── base_agent.py
│   │   │   ├── technical_analyst.py   # 技术分析师
│   │   │   ├── fundamentals_analyst.py# 基本面分析师
│   │   │   ├── news_analyst.py        # 新闻分析师
│   │   │   ├── sentiment_analyst.py   # 情绪分析师
│   │   │   ├── risk_manager.py        # 风险管理员
│   │   │   └── researcher_team.py     # 研究团队
│   │   ├── services/         # 业务服务
│   │   └── main.py           # FastAPI 入口
│   └── requirements.txt
│
├── docker/                   # Docker 部署
│   ├── docker-compose.yml          # 主编排 (redis/mysql/backend)
│   ├── docker-compose.collector.yml# 采集层编排
│   ├── backend/
│   │   ├── Dockerfile.dev          # 后端开发 Dockerfile
│   │   └── Dockerfile.mvn          # Maven 构建 Dockerfile
│   ├── collector/
│   │   └── Dockerfile              # 采集器 Dockerfile
│   └── mysql/
│       └── init.sql                # 数据库初始化 SQL
│
├── docs/                     # 项目文档
│   ├── design/               # 设计文档
│   │   ├── ARCHITECTURE.md          # 完整架构 (28 张表/索引/Redis Key)
│   │   ├── project-structure.md     # 项目结构手册
│   │   ├── requirements.md          # 需求文档
│   │   ├── ui-analysis-report.md    # UI 分析报告
│   │   ├── architecture_report.json # 架构评估 JSON
│   │   ├── api/                     # API 文档
│   │   └── security/               # 安全文档
│   ├── data_gap_report_final.md     # 数据缺口报告 (最终版)
│   └── 缠论资料/                   # 缠论算法研究资料
│       └── *.caj                   # 4 篇缠论研究论文
│
├── scripts/                  # 运维脚本
│   ├── deploy.ps1            # 部署脚本
│   ├── deploy-layers.ps1     # 分层部署
│   ├── deploy-rollback.ps1   # 回滚脚本
│   ├── deploy-config.json    # 部署配置
│   ├── health_check.py       # 健康检查
│   ├── diagnose_env.ps1      # 环境诊断
│   ├── git-push-to-remote.sh # Git 推送
│   └── start-session.ps1    # 开发会话启动
│
├── analysis-algorithms/      # 分析算法 (Python)
│   ├── chanlun_bridge.py       # 缠论分析 Bridge (后端调用)
│   └── ...
│
├── logs/                     # 日志目录
├── data/                     # 数据 (MySQL/Redis/CSV)
├── CHANGELOG.md              # 变更日志
└── README.md                 # 本文件
```

---

## 5. 目录与文件详解

### `data-collector/` — 数据采集层

| 文件 | 用途 | 技术亮点 |
|:-----|:-----|:---------|
| `auto_seed.py` | **核心管道**: 每分钟/每30分钟循环，直取腾讯API行情 → CSV → Redis | 原生 socket RESP 协议写入，零外部依赖 |
| `seed_kline.py` | K 线全量采集 (5542只, ~26min) | 20 并发 HTTP，分批写入 Redis |
| `write_kline_to_redis.py` | 将 CSV 格式 K 线写入 Redis | 批量 pipeline 写入 |
| `hdfs_upload.py` | 可选: 上传 CSV 到 HDFS 数据湖 | |
| `hdfs_to_redis.py` | 可选: 从 HDFS 分析结果写入 Redis | Spark 分析结果同步 |
| `scheduler/run_collector.py` | **PID 1 主进程**: 交易时段1分钟/非交易30分钟调度 | 交易时段感知，绕过熔断器 |
| `collectors/tencent_collector.py` | 腾讯财经 API 采集 (实时行情/指数) | 包装 HTTP 请求 |

### `backend/` — 后端 API

| Controller | 职责 | 端点前缀 |
|:-----------|:------|:---------|
| `RedisDataController` | 市场数据直读 Redis (分页列表/详情/K线/搜索) | `/api/v2/market/*` |
| `IndexController` | 指数列表/详情/K线 | `/api/v2/index/*` |
| `SignalDataController` | 信号数据 (北向/龙虎榜/题材/资金流) | `/api/v2/signal/*` |
| `AnalysisController` | 缠论分析/Python Bridge | `/api/analysis/*` |
| `UserController` | 用户登录/注册/信息 | `/api/user/*` |
| `InfoController` | 资讯/研报/公告/预期 | `/api/v2/info/*` |
| `FundController` | 基金列表/净值 | `/api/v2/fund/*` |
| `SecurityController` | 安全配置/权限 | `/api/security/*` |
| `WatchlistController` | 自选股管理 | `/api/v2/watchlist/*` |
| `MarketController` | 部分历史端点 | 迁移中 |

### `frontend/` — 前端

| 子目录 | 说明 |
|:-------|:------|
| `api/` | 20 个 API 模块，axios 封装 + 请求缓存 |
| `views/` | 33 个页面 (大盘/个股/登录/资讯/基金/标志/解禁/预期等) |
| `components/chart/` | 核心图表组件: K 线 (`KLineChart.vue`)、行业云图、缠论渲染 |
| `components/common/` | EmptyState、SkeletonLoader 等通用组件 |
| `composables/` | `useTechnicalChart.ts` — K 线缩放+缠论+技术指标组合 |
| `stores/` | Pinia stores (user/auth) |
| `router/` | Vue Router 路由配置 |
| `utils/` | format.ts (价格/百分比格式化) 等 |

### `ai-service/` — AI 服务 (可选)

| Agent | 职责 |
|:------|:------|
| `technical_analyst` | 技术指标分析 (MA/MACD/RSI/KDJ/Bollinger) |
| `fundamentals_analyst` | 基本面分析 (PE/PB/ROE/营收/利润) |
| `news_analyst` | 新闻事件分析 |
| `sentiment_analyst` | 市场情绪分析 |
| `risk_manager` | 风险评估 (波动率/最大回撤/系统风险) |
| `researcher_team` | 综合研究团队 (多 Agent 协同) |

---

## 6. API 端点

### 市场数据 (`/api/v2/market`)

| 端点 | 说明 | Redis Key |
|:-----|:-----|:----------|
| `GET /list` | 股票分页列表 (5542 只) | `market:stock_basic` |
| `GET /detail/{code}` | 个股详情 | `market:stock_basic` (filter) |
| `GET /kline/{code}` | 日 K 线 (120 条) | `market:kline_{code}` |
| `GET /kline/range` | K 线范围查询 | `market:kline_{code}` |
| `GET /search` | 全局搜索 | `market:stock_basic` |
| `GET /sector-ranking` | 行业涨跌排行 (5542 条) | `market:sector_ranking` |
| `GET /industry-treemap` | 行业云图 (99 个行业) | `market:industry_treemap` |
| `GET /max-date` | 最新交易日 | `market:max_date` |

### 指数 (`/api/v2/index`)

| 端点 | 说明 | Redis Key |
|:-----|:-----|:----------|
| `GET /list` | 指数列表 (含实时价, K 线修正) | `market:index_list` |
| `GET /{code}` | 指数详情 | `market:index_list` |
| `GET /{code}/kline` | 指数 K 线 | `market:index_kline_{code}` |

### 信号 (`/api/v2/signal`)

| 端点 | 说明 | Redis Key |
|:-----|:-----|:----------|
| `GET /hot-reason` | 题材热点 (96 只) | `market:hot_reason` |
| `GET /dragon-tiger/daily` | 龙虎榜 (75 条) | `market:dragon_tiger` |
| `GET /northbound/latest` | 北向资金 (最后 50 条) | `market:northbound` |
| `GET /fund-flow/{code}` | 资金流向 | `market:fund_flow` |
| `GET /lockup-detail/{code}` | 限售解禁 | `market:lockup_detail` |
| `GET /industry-compare` | 行业对比 | `market:industry_compare` |

### 分析 (`/api/analysis`)

| 端点 | 说明 | 数据源 |
|:-----|:-----|:-------|
| `GET /{code}/chanlun` | 缠论分析 | Redis K 线 + Python Bridge |
| `GET /{code}/technical` | 技术指标 | Redis K 线计算 |
| `GET /{code}/trend` | 趋势分析 | Redis |
| `GET /{code}/yearly-return` | 年收益率 | Redis |
| `POST /filter` | 多条件筛选 | MySQL |

### 资讯 (`/api/v2/info`)

| 端点 | 说明 | 数据源 |
|:-----|:-----|:-------|
| `GET /cls-news` | 财联社快讯 | MySQL |
| `GET /global-news` | 全球资讯 | MySQL |
| `GET /research/{code}` | 个股研报 | MySQL |
| `GET /filings/{code}` | 公司公告 | MySQL |
| `GET /consensus-eps/{code}` | 一致预期 | MySQL |

### 用户/基金

| 端点 | 说明 |
|:-----|:-----|
| `POST /api/user/login` | 登录 → JWT Token |
| `POST /api/user/register` | 注册 |
| `GET /api/user/info` | 用户信息 (需 Bearer Token) |
| `GET/POST/DELETE /api/v2/watchlist/*` | 自选管理 |
| `GET /api/v2/fund/list` | 基金列表 |
| `GET /api/v2/fund/nav/{code}` | 基金净值 |

---

## 7. Redis Key 设计

| Key | 类型 | TTL | 写入方 | 说明 |
|:----|:-----|:---:|:-------|:-----|
| `market:kline_{code}` | String(JSON) | 12h | `seed_kline.py` | 个股日 K 线 (120 条) |
| `market:index_kline_{code}` | String(JSON) | 24h | `seed_kline.py` | 指数日 K 线 (120 条) |
| `market:stock_basic` | String(JSON) | 1h | `auto_seed.py` | 5,542 只实时行情 |
| `market:index_list` | String(JSON) | 1h | `auto_seed.py` | 5 只指数 (K 线修正) |
| `market:sector_ranking` | String(JSON) | 1h | `auto_seed.py` | 个股涨跌排行 (5542) |
| `market:stats` | String(JSON) | 1h | `auto_seed.py` | 涨跌统计 |
| `market:hot_reason` | String(JSON) | 1h | `auto_seed.py` | 题材热点归因 |
| `market:northbound` | String(JSON) | 1h | `auto_seed.py` | 北向资金 (最后 50 条) |
| `market:dragon_tiger` | String(JSON) | 1h | `auto_seed.py` | 龙虎榜 |
| `market:industry_treemap` | String(JSON) | 1h | `auto_seed.py` | 行业云图 (99 行业) |
| `market:industry_compare` | String(JSON) | 1h | `auto_seed.py` | 行业对比 |
| `market:fund_flow` | String(JSON) | 24h | `auto_seed.py` | 资金流向 |
| `market:lockup_detail` | String(JSON) | 24h | `auto_seed.py` | 限售解禁 |
| `market:max_date` | String(JSON) | 1h | `auto_seed.py` | 最新交易日 |
| `market:stock_industry` | String(JSON) | 7d | `auto_seed.py` | 行业映射 |

---

## 8. 数据库设计

MySQL 仅承载**业务数据**（用户/自选/资讯/信号），约 **20 张表、~400 万条记录**。

### 业务表

| 表 | 行数 | 说明 |
|:---|:----:|:-----|
| `user` | ~10 | 用户 |
| `watchlist` | ~10 | 自选股 |
| `ai_chat` | 0 | AI 对话记录 |
| `analysis_result` | ~200 | 分析结果 |

### 资讯表

| 表 | 行数 | 说明 |
|:---|:----:|:-----|
| `info_cls_news` | ~25K | 财联社快讯 |
| `info_global_news` | ~280K | 全球资讯 |
| `info_research_report` | ~6K | 研究报告 |
| `info_filing` | ~5K | 公司公告 |
| `info_consensus_eps` | ~900 | 一致预期 |
| `info_stock_news` | ~4K | 个股新闻 |

### 信号表

| 表 | 行数 | 说明 |
|:---|:----:|:-----|
| `signal_hot_reason` | ~28K | 题材热点 |
| `signal_dragon_tiger` | ~25K | 龙虎榜 |
| `signal_dragon_tiger_detail` | ~30K | 龙虎榜明细 |
| `signal_fund_flow` | ~5K | 资金流向 |
| `signal_lockup_detail` | ~27K | 限售解禁 |

> 完整数据库设计（含字段定义、索引策略）详见 `docs/design/ARCHITECTURE.md`

---

## 9. 部署

### 前置条件

- Docker Engine ≥ 20.10
- Docker Compose v2+

### 启动所有服务

```powershell
cd f:\bs\A_system\docker

# 启动存储层 (Redis + MySQL)
docker compose up -d redis mysql

# 启动后端
docker compose up -d backend

# 启动采集层
docker compose -f docker-compose.collector.yml up -d
```

### 数据初始化

```powershell
# K 线首次采集 (全量 5542 只, ~26 分钟)
docker exec data-collector python3 /app/seed_kline.py

# Redis 全量数据刷新
docker exec data-collector python3 /app/auto_seed.py
```

### 停止

```powershell
cd f:\bs\A_system\docker
docker compose down
docker compose -f docker-compose.collector.yml down
```

---

## 10. 开发指南

### 本地开发

```powershell
# 后端 (需 MySQL + Redis 运行)
cd backend
mvn spring-boot:run
# → http://localhost:8082/swagger-ui/index.html

# 前端 (需后端运行)
cd frontend
npm install
npm run dev
# → http://localhost:5173

# AI 服务
cd ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Vite 代理

本地开发时，`frontend/vite.config.ts` 自动代理 `/api` → `http://localhost:8082`。

### AI 对话

`ai-service/.env` 配置 SiliconFlow API Key：

```bash
SILICONFLOW_API_KEY=sk-your-key-here
SILICONFLOW_MODEL=Qwen/Qwen2.5-72B-Instruct
```

无 API Key 时自动降级为模拟回复。

---

## 11. 运行验证

```powershell
# 验证后端
curl http://localhost:8082/api/v2/market/list?page=1&size=5

# 验证 K 线
curl http://localhost:8082/api/v2/market/kline/000001?days=3

# 验证指数
curl http://localhost:8082/api/v2/index/list

# 验证涨跌统计
docker exec redis redis-cli GET market:stats

# 验证 Redis 数据量
docker exec redis redis-cli DBSIZE

# 打开前端
# http://localhost:5173
```

---

## 12. 变更日志

### v4.1 (2026-06-03)

| 变更 | 详细 |
|:-----|:------|
| **重构后端** | 重建后端容器，修复 JDK 版本兼容、数据库连接、JWT 密钥问题 |
| **移除** | 14 个废弃 Docker 容器 + 22 个无用镜像 + 35 个无用卷 |
| **移除** | `bigdata-processing/`、`a-stock-data-temp/`、`target/` 目录 |
| **移除** | 80+ 个废弃 Python/Shell 脚本 (Hadoop/Hive/Spark 依赖) |
| **优化** | 涨跌排行改为 sector-ranking 全量数据前端排序，移除不存在的 analysis 端点 |
| **优化** | 北向资金修复字段兼容性 (`time`/`trade_date`)，取最后 50 条 |
| **优化** | 前端 403 响应处理 (token 过期自动跳登录) |
| **修复** | **Vite 代理 502** — 残留的 `/api/analysis → 8899` 规则指向已删除的缠论独立服务，改为统一 `/api → 8082` |
| **修复** | **缠论 ECharts notMerge** — `useTechnicalChart.ts` 添加 `notMerge: true`，确保 markArea/markPoint 正确渲染 |
| **修复** | **指数缠论数据混合** — Java 控制器传 `preferIndex`、bridge 自动检测以 `0/399` 开头的指数代码并加载指数 K 线 |
| **修复** | **桥梁脚本 stderr** — `os.dup2(/dev/null)` 禁用 Python 日志输出，清除 Spring @Cacheable 缓存 |
| **文档** | 更新 README，创建 `docs/design/` 目录，归档设计文档 |

### v4.0 (2026-06-01)

- Hadoop/Hive/Spark/Kafka/Zookeeper/Prometheus/Grafana 全部移除
- 新增 `seed_kline.py`、`auto_seed.py` 零依赖管道
- 新增缠论分析、行业云图、题材热点等前端页面
- Redis 替代 Hive 成为主数据源
- 清理 103 个废弃文件

---

> **注意**: 本项目代码仅供学习参考，不构成任何投资建议。投资有风险，入市需谨慎。
>
> **License**: MIT License — Copyright (c) 2026 A_system
