# 基金股票智能分析系统

基于 **Hadoop 生态 + 多智能体决策** 的金融大数据分析平台，覆盖数据采集、大数据处理、算法分析、后端 API、前端展示、AI 智能对话全链路。

---

## 目录

- [1. 系统概述](#1-系统概述)
- [2. 系统架构](#2-系统架构)
- [3. 层次交互与协作机制](#3-层次交互与协作机制)
- [4. 数据流向详解](#4-数据流向详解)
- [5. 接口调用链路](#5-接口调用链路)
- [6. 核心模块详解](#6-核心模块详解)
- [7. 部署架构](#7-部署架构)
- [8. 部署环境与配置](#8-部署环境与配置)
- [9. 部署流程](#9-部署流程)
- [10. 运行验证](#10-运行验证)
- [11. 开发指南](#11-开发指南)

---

## 1. 系统概述

### 1.1 项目定位

覆盖 "数据采集 → 大数据处理 → 算法分析 → 后端 API → 前端展示 → AI 智能对话" 全链路的金融智能分析平台。提供实时行情、技术指标计算、缠论分析、量化回测、多智能体 AI 对话等完整功能。

### 1.2 核心技术栈

| 层 | 技术 | 版本 |
|:---|:-----|:----:|
| **数据采集** | Python HTTP/TCP 直连 (容器化) | 3.11 |
| **大数据存储** | HDFS / Hive / MySQL 8.0 | Hadoop 3.2.1 / Hive 2.3.2 |
| **大数据计算** | PySpark 3.x / MapReduce (共享配置模块) | Spark 3.5.0 |
| **算法分析** | Python 原生实现 | 3.11 |
| **后端 API** | Java / Spring Boot 3 / MyBatis-Plus | Java 17 / SB 2.7.18 |
| **前端** | Vue 3 / TypeScript / ECharts / Element Plus | Vue 3.4 |
| **AI 服务** | Python FastAPI / DeepSeek / 多智能体架构 | FastAPI |
| **部署** | Docker Compose (双层隔离架构) | 20+ |
| **缓存** | Redis | 7-alpine |
| **消息队列** | Kafka + Zookeeper (跨层桥接) | 7.5.0 |
| **监控** | Prometheus + Grafana | 2.51 / 10.4 |

---

## 2. 系统架构

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户 (浏览器)                                 │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTP :80
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 2: 大数据层 (bigdata-net — 172.19.0.x)                           │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │  Nginx 反向代理 (端口 80)                                            │ │
│ │  / → Vue 3 SPA  /api/ → Backend :8082  /ai/ → AI Service :8000     │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│        │                            │                           │      │
│        ▼                            ▼                           ▼      │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │  应用服务层 (Tier 3)                                                  │ │
│ │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │ │
│ │  │  Vue 3 前端      │  │ Spring Boot 后端 │  │ FastAPI AI 服务  │  │ │
│ │  │  (Nginx, :80)    │  │ (Java 17, :8082) │  │ (Python, :8000)  │  │ │
│ │  └──────────────────┘  └────────┬─────────┘  └──────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │  基础设施存储 (Tier 1)                                                │ │
│ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│ │  │  MySQL 8.0    │  │  Redis 7     │  │  HDFS        │              │ │
│ │  │  (3306)       │  │  (6379)      │  │  NameNode    │              │ │
│ │  │  16 张业务表   │  │  TTL=30min   │  │  + DataNode×2│              │ │
│ │  └──────┬───────┘  └──────────────┘  └──────┬───────┘              │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                        │                           │                    │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │  大数据计算引擎 (Tier 2)                                              │ │
│ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │ │
│ │  │  YARN (RM)   │  │  Hive 2.3.2 │  │  Spark 3.5.0 (Master    │  │ │
│ │  │  (8088)      │  │  (10000)    │  │    + Worker, :8080)      │  │ │
│ │  └──────────────┘  └──────┬───────┘  │  7 Batch + 1 Streaming  │  │ │
│ │                           │           │  共享 spark_config 模块  │  │ │
│ │                           │           └──────────────────────────┘  │ │
│ │                           ▼                                         │ │
│ │  ┌─ ORC 格式优化表 (比 TEXTFILE 快 5~15x) + 5 UDF (新增) ────┐   │ │
│ │  │  7 DDL + 8 DML + 5 UDF (extract_code/classify_change...)   │   │ │
│ │  └─────────────────────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ Kafka :39092 (双网卡桥接)     │ 共享卷 :ro (CSV 批量导入)
        │                              │
┌───────┴──────────────────────────────┴─────────────────────────────────┐
│  Layer 1: 数据采集层 (collector-net — 172.20.0.x, 独立网络隔离)        │
│                                                                        │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Zookeeper    │  │  Kafka 7.5.0    │  │  data-collector          │  │
│  │  (2181)       │──│  (29092/39092)  │◀─│  (Python 容器化)          │  │
│  │               │  │  3分区, 7天保留  │  │  6 数据源工厂模式        │  │
│  └──────────────┘  └──────────────────┘  │  熔断器 + 限流 + 重试    │  │
│                                           └──────────┬───────────────┘  │
│                                                      │                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  外部数据源: 腾讯财经 / 同花顺 / 百度股市通 / 通达信TCP / akshare  │   │
│  │  优先级: mootdx(10) > tencent(9) > ths(8) > baidu(7) > akshare(6)│   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────────────┐
│                   数据采集层                                             │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ 腾讯财经  │ │ 同花顺   │ │ 百度股市通│ │ 通达信TCP │ │ akshare  │    │
│  │ (HTTP)   │ │ (HTTP)   │ │ (HTTP)   │ │ (TCP)    │ │ (HTTP)   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────┐                        │
│  │  DataSourceFactory (工厂模式 + 故障转移)     │                        │
│  │  优先级: mootdx(10) > tencent(9) > ths(8)  │                        │
│  │  > baidu(7) > akshare(6)                   │                        │
│  └─────────────────────┬──────────────────────┘                        │
│                        │                                                │
│               ┌────────┴────────┐                                       │
│               ▼                ▼                                        │
│        CSV (本地)         HDFS 双写                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 层次划分

系统共分为 **6 个逻辑层** + **2 个 Docker 部署层**：

#### Docker 部署分层

| 部署层 | Docker Compose | 网络 (子网) | 包含逻辑层 |
|:-------|:---------------|:------------|:-----------|
| **L1 数据采集层** | `docker-compose.collector.yml` | `collector-net` (172.20.0.x) | L1 数据采集 |
| **L2 大数据层** | `docker-compose.yml` | `bigdata-net` (172.19.0.x) | L2~L6 (大数据处理 + 算法 + 后端 + AI + 前端) |

#### 逻辑层次

| 层次 | 模块路径 | 职责 |
|:-----|:---------|:-----|
| **L1 数据采集** | `data-collector/` | 从 6 个外部数据源采集实时行情、K 线、资金流向等 |
| **L2 大数据处理** | `bigdata-processing/` | Hive SQL 分析 + Spark 批处理/流计算 + MapReduce (spark_config 共享模块) |
| **L3 算法分析** | `analysis-algorithms/` | 技术指标、缠论、量化策略、回测引擎 |
| **L4 后端 API** | `backend/` | Spring Boot REST API + JWT 认证 + Redis 缓存 |
| **L5 AI 服务** | `ai-service/` | 多智能体 AI 对话 + DeepSeek/模拟降级 |
| **L6 前端展示** | `frontend/` | Vue 3 SPA + ECharts 可视化 + Element Plus UI |

---

## 3. 层次交互与协作机制

### 3.1 各层协作全景

```
用户操作
   │
   ▼
┌──────────────┐    Nginx 反向代理 (端口 80)
│  Vue 3 前端   │─────────────────────────────────────────────┐
│  (L6)         │                                             │
│               │   /api/ (Axios 请求, 15s 超时)              │
│  Pinia Store  │─────────────────────────────────────────┐   │
│  ────────     │  GET /api/stock/list                    │   │
│  stock store  │  POST /api/user/login                   │   │
│  user store   │  GET /api/analysis/...                  │   │
│               │  POST /api/ai/chat                      │   │
└───────────────┘                                         │   │
                                                          │   │
   /ai/ (Axios 请求)                                      │   │
   ───────────────────────────────────────────────────┐   │   │
                                                      │   │   │
                                                      ▼   ▼   ▼
                                             ┌──────────────────────┐
                                             │  Spring Boot 后端    │
                                             │  (L4)                │
                                             │                      │
                                             │  7 Controller        │
                                             │  ├─ StockController   │
            ┌─────────────────────────────►  │  ├─ FundController    │
            │                                │  ├─ AnalysisController│
            │  后端 Api (httpx, 5s 超时)      │  ├─ AIController     │
            │                                │  ├─ UserController   │
            │                                │  ├─ WatchlistCon...  │
            │                                │  └─ SignalController │
            │                                │                      │
            │                                │  14 Service          │
            │                                │  14 MyBatis Mapper   │
            │                                │  JWT Security Filter │
            │                                │  Redis Cache (30min) │
            │                                └──────┬───────────────┘
            │                                       │
            │                                       ▼
            │                               ┌───────────────┐
            │                               │    MySQL      │
            │                               │   16 张表     │
            │                               └───────────────┘
            │
            ▼
┌──────────────────────┐
│  FastAPI AI 服务     │
│  (L5)                │
│                      │
│  DialogueService     │
│  ────────────────    │
│  _build_context()    │
│  并行调用后端 3 个    │
│  API 获取实时数据：   │
│  1. /api/stock/{code}│
│  2. /api/analysis/   │
│     technical/{code} │
│  3. /api/signal/     │
│     overview/{code}  │
│                      │
│  → 组装 system context│
│  → 发送给 AI 模型     │
│  → 返回分析回复       │
└──────────────────────┘
```

### 3.2 L1 → L2 → L3 协作（数据处理管道）

```
L1: 数据采集层
┌──────────────────────────────────────────────────────────────┐
│  market_collect.py / run_collector.py                        │
│                                                              │
│  6 数据源 → DataSourceFactory                                 │
│    ├─ tencent       → 实时行情 CSV (realtime_*.csv)           │
│    ├─ ths_hot       → 题材归因 CSV (hot_reason_*.csv)         │
│    ├─ ths_northbound→ 北向资金 CSV (northbound_*.csv)         │
│    ├─ baidu         → 概念板块 JSON (concept_blocks_*.json)   │
│    ├─ akshare_ext   → 龙虎榜/行业/研报 JSON                   │
│    └─ mootdx(TCP)   → 历史 K 线 CSV (kline_*_daily_*.csv)    │
│                                                              │
│  输出格式: CSV + JSON → data/raw/                             │
│                                                              │
│  双写管道 (run_with_hdfs.py):                                  │
│    CSV → MySQL (sync_to_mysql.py)                             │
│    CSV → HDFS (upload_to_hdfs.py)                             │
└──────────────────────────────────────────────────────────────┘
        │
        ▼  CSV 数据落盘
┌──────────────────────────────────────────────────────────────┐
│  兜底恢复机制: restore_from_hdfs.py                           │
│  HDFS → Hive → CSV → MySQL                                   │
└──────────────────────────────────────────────────────────────┘

L2: 大数据处理层
┌──────────────────────────────────────────────────────────────┐
│  run_batch_pipeline.py (批处理管道调度器)                      │
│                                                              │
│  步骤 1: Hive MSCK REPAIR TABLE stock_daily                   │
│                                                              │
│  步骤 2: Hive DML 分析 (6 个 SQL 顺序执行)                    │
│    ├─ analysis_daily.sql         → 日均价统计                  │
│    ├─ analysis_change.sql        → 涨跌幅统计排行              │
│    ├─ analysis_correlation.sql   → Pearson 相关系数            │
│    ├─ analysis_year_comparison.sql→ 年同比分析                 │
│    ├─ analysis_technical.sql     → MA/RSI 技术指标 SQL         │
│    └─ analysis_signal_fusion.sql → 信号融合分析                │
│                                                              │
│  步骤 3: Spark 批处理 (7 个 Job 顺序执行)                     │
│    ├─ yearly_return.py          → 年收益率排名                 │
│    ├─ monthly_return.py         → 月收益率排名                 │
│    ├─ ma_trend.py               → 金叉/死叉信号               │
│    ├─ correlation.py            → 相关系数矩阵                 │
│    ├─ sector_ranking.py         → 行业涨跌排行                 │
│    ├─ filter_stocks.py          → PE/PB/ROE 筛选              │
│    └─ trend_judge.py            → 趋势判断                     │
│    └─ stock_predictor.py       → MLlib 股票预测原型 (新增)    │
│                                                              │
│  支持 3 种模式: daily / incremental / rebuild                 │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
L3: 算法分析层 (Python 原生, 不依赖 Hadoop)
┌──────────────────────────────────────────────────────────────┐
│  analysis-algorithms/                                        │
│                                                              │
│  技术指标 (technical/)                                       │
│    ma.py          → MA5/10/20/60 + 金叉/死叉                 │
│    macd.py        → EMA12/26/DIF/DEA/MACD + 背离             │
│    kdj.py         → RSV/K/D/J + 超买/超卖                    │
│    rsi.py         → RSI6/12/24 + Wilders 平滑                │
│    bollinger.py   → 中轨/上轨/下轨/带宽/%B                   │
│                                                              │
│  缠论 (chanlun/) — 6 步递归分解                               │
│    Step 1: K 线包含处理 (merge_klines)                        │
│    Step 2: 分型识别 (顶分型/底分型)                            │
│    Step 3: 笔识别 (上升笔/下降笔)                              │
│    Step 4: 线段识别 (至少3笔)                                  │
│    Step 5: 中枢识别 (ZG/ZD)                                   │
│    Step 6: 买卖信号 (三类买/卖点)                              │
│                                                              │
│  量化策略 (quantitative/)                                     │
│    ma_strategy.py           → 均线金叉买入/死叉卖出            │
│    momentum_strategy.py    → 动量策略                         │
│    multi_factor_strategy.py→ 多因子策略                       │
│    backtest.py             → 回测引擎                         │
│      (总收益率/年化/最大回撤/夏普比率/胜率)                    │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 AI 多智能体协作机制

```
用户消息 "分析 600519 贵州茅台"
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  DialogueService.chat(message, stock_code, history)         │
│                                                             │
│  1. _build_context("600519") — 并行调用后端 3 个 API        │
│     ┌────────────────────────────────────────────┐          │
│     │ httpx.AsyncClient (5s 超时)                │          │
│     │                                           │          │
│     │ GET /api/stock/600519          → 实时行情  │          │
│     │ GET /api/analysis/technical/600519 → 技术指标│        │
│     │ GET /api/signal/overview/600519 → 市场信号 │          │
│     └──────────────────┬─────────────────────────┘          │
│                        ▼                                    │
│  2. 组装 System Context:                                    │
│     "标的: 600519 实时行情: 贵州茅台 股价... PE=...          │
│      技术指标: MA5=... MA20=... MACD_DIF=...                │
│      市场信号: 题材热度... 北向资金..."                      │
│                                                             │
│  3. 构建消息列表 (System Prompt + Context + History + User) │
│                                                             │
│  4. 发送给 AIClient.chat()                                  │
│     ├─ 有 API Key → DeepSeek API (httpx POST, 30s 超时)    │
│     │              → 返回真实 AI 分析                       │
│     └─ 无 API Key → _mock_reply() (模拟回复)                │
│                      → 根据关键词匹配模板                    │
│                      → template.format(mock_data)           │
│                                                             │
│  5. 返回 {"reply": "分析结果..."}                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼  同时可选启动多智能体深度分析
┌─────────────────────────────────────────────────────────────┐
│  MultiAgentService.analyze_stock("600519")                  │
│                                                             │
│  7 个 Agent 顺序执行 (每个 4s 超时):                         │
│                                                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │  1. FundamentalsAnalyst  (基本面分析)             │       │
│  │     → PE/PB/市值/盈利能力 → 估值判断               │       │
│  │                                                   │       │
│  │  2. TechnicalAnalyst      (技术分析)              │       │
│  │     → 均线/MACD/RSI/KDJ/布林带 → 技术面信号        │       │
│  │                                                   │       │
│  │  3. SentimentAnalyst      (情绪分析)              │       │
│  │     → 题材热度/北向资金/主力资金 → 市场情绪        │       │
│  │                                                   │       │
│  │  4. NewsAnalyst           (新闻分析)              │       │
│  │     → 新闻/公告/研报 → 事件驱动信号                │       │
│  │                                                   │       │
│  │  5. ResearcherTeam        (研究员讨论, 3轮辩论)    │       │
│  │     → 多 Agent 迭代辩论 → 综合研判                 │       │
│  │                                                   │       │
│  │  6. TraderAgent           (交易决策)              │       │
│  │     → 综合以上分析 → 买入/卖出/持有 + 仓位/止损    │       │
│  │                                                   │       │
│  │  7. RiskManager           (风险评估)              │       │
│  │     → 审核交易决策 → 风险评级 + 最终裁定           │       │
│  └──────────────────────────────────────────────────┘       │
│                                                             │
│  → 返回 {"stock_code": "600519", "reports": {...}}          │
│                                                             │
│  记忆服务 (MemoryService):                                   │
│    自动保存历史决策 → 支持 auto_reflect() 反思对比           │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 数据流向详解

### 4.1 实时数据流（用户查询 → 前端展示）

```
用户打开股票列表页
       │
       ▼
Vue 3 StockListView.vue onMounted()
       │
       ├── useStockStore() → 调用 API
       │
       ▼
api/stock.ts → getStockList({page, size, keyword, industry, sort})
       │
       ▼
Axios GET /api/stock/list
       │
       ▼  (通过 Vite proxy 转发到后端)
       │
Spring Boot StockController.list()
       │
       ├── @Cacheable(value="stocks", key="#params") → Redis 查询
       │      ├── 命中 → 直接返回缓存数据 (TTL=30分钟)
       │      └── 未命中 → 继续执行
       │
       ├── StockService.listWithMarketData(params)
       │      └── StockMapper.selectPage(page, wrapper) → MySQL
       │
       └── 返回 PageResponse<StockRecord> + 写入 Redis 缓存
               │
               ▼
       Vue 前端展示 Element Plus Table + ECharts 图表
```

### 4.2 批处理数据流（采集 → 分析 → 入库）

```
[交易日晚间 18:00]
       │
       ▼
Layer 1 (collector-net): 数据采集
  docker compose -f docker-compose.collector.yml up -d
       │
       ├── Kafka (实时流) → Spark Streaming (大数据层消费)
       └── 共享卷 stock-collector-data (CSV 批量)
              │
              ▼  ingest_collector_data.sh 或 共享卷 :ro 挂入 NameNode
              │
Layer 2 (bigdata-net): 大数据处理
  python run_batch_pipeline.py --mode daily [--parallel] [--skip-hive]
       │
       ├── Phase 0: 环境检查 (HDFS/Hive 可用性)
       │
       ├── Phase 1: Hive DML (6 个 SQL, 按依赖顺序执行)
       │     ├── analysis_daily.sql          → 日均价统计
       │     ├── analysis_correlation.sql    → Pearson 相关系数
       │     ├── analysis_change.sql         → 涨跌幅统计排行
       │     ├── analysis_year_comparison.sql→ 年同比分析
       │     ├── analysis_technical.sql      → MA/RSI 技术指标
       │     └── analysis_signal_fusion.sql  → 信号融合分析
       │
       ├── Phase 2: Spark 批处理 (7 个 Job, 可并行执行)
       │     ├── ma_trend.py      (共享 spark_config 模块)
       │     ├── trend_judge.py   ↓ 消除 7 处重复代码
       │     ├── filter_stocks.py → 统一配置管理
       │     ├── correlation.py   → 统一 HDFS 输出路径
       │     ├── sector_ranking.py→ AQE 自适应优化
       │     ├── monthly_return.py→ Parquet Snappy 压缩
       │     └── yearly_return.py
       │
       ├── Phase 3: 数据质量检查 (QC 门禁)
       │     ├── 行数验证 (对比源表)
       │     ├── 空值率检查
       │     └── HDFS 输出目录验证
       │
       ├── ORC 格式 Hive 表 (比 TEXTFILE 快 5~15x)
       │     └── migrate_hive_to_orc.py 一键迁移脚本
       │
       └── HDFS 备份管道 (v2)
             ├── 全量备份 / 增量备份
             ├── 并行导出 + 自动清理 (30 天保留)
             └── 备份清单 JSON + 校验对比
                    │
                    ▼
L4: 后端查询预计算结果
  AnalysisController → AnalysisService → AnalysisResultMapper
       │
       └── 返回给前端 ECharts 渲染
```

### 4.3 故障降级流

```
┌──────────────────────────────────────────────────────────────────┐
│ 场景 1: 数据采集故障                                              │
│  DataSourceFactory.collect_with_fallback()                       │
│    mootdx(10) → tencent(9) → ths(8) → baidu(7) → akshare(6)    │
│    前一个失败自动切换到下一个                                     │
│                                                                  │
│ 场景 2: AI API Key 未配置                                        │
│  AIClient.chat() → mock_mode=True                                │
│    ├─ 关键字匹配: "涨"/"跌"/"缠论"/"基金"/"大盘"                 │
│    ├─ 选择对应模板: trend_bullish / trend_bearish / chanlun_buy  │
│    └─ template.format(mock_data) → 返回模拟分析                  │
│                                                                  │
│ 场景 3: AI API 调用超时/失败                                      │
│  AIClient._real_chat() → Exception                              │
│    └─ 自动 fallback 到 _mock_reply()                             │
│                                                                  │
│ 场景 4: 后端 API 不可用 (AI 服务调用后端行情)                     │
│  DialogueService._build_context() → httpx 超时 5s               │
│    └─ 跳过该数据源，仅使用已有上下文                               │
│                                                                  │
│ 场景 5: HDFS/Hive 不可用                                         │
│  BatchPipeline.run_step() → FileNotFoundError                   │
│    └─ 标记为 skipped，不中断管道                                  │
│                                                                  │
│ 场景 6: Redis 不可用                                             │
│  @Cacheable → 缓存穿透 → 直接查询 MySQL                          │
│    └─ 不影响业务功能，仅性能下降                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. 接口调用链路

### 5.1 前端 → 后端 API (通过 Nginx 反向代理)

所有前端 API 请求统一经 Axios 实例处理:

```
Axios Instance: baseURL="/api", timeout=15000ms
  ├── 请求拦截器: 从 localStorage 获取 JWT token → Authorization: Bearer <token>
  └── 响应拦截器: 401 状态码 → 自动跳转 /login
```

#### 股票模块

| 前端函数 | HTTP | 后端端点 | 说明 |
|:---------|:----:|:---------|:-----|
| `getStockList()` | GET | `/stock/list` | 分页+搜索+行业筛选+排序 |
| `getStockByCode(code)` | GET | `/stock/{code}` | 详情含最新行情 |
| `getKlineData(code)` | GET | `/stock/kline/{code}` | 日K线 (支持 freq=daily/weekly/monthly) |
| `searchStocks(keyword)` | GET | `/stock/search` | 自动补全搜索 |
| `getIndustries()` | GET | `/stock/industries` | 行业列表 |

#### 分析模块

| 前端函数 | HTTP | 后端端点 | 说明 |
|:---------|:----:|:---------|:-----|
| `getYearlyReturn(code)` | GET | `/analysis/{code}/yearly-return` | 年收益率 |
| `getMonthlyReturn(code)` | GET | `/analysis/{code}/monthly-return` | 月收益率 |
| `getTrend(code)` | GET | `/analysis/{code}/trend` | 趋势分析 (上升/下跌/震荡) |
| `filterStocks(conditions)` | POST | `/analysis/filter` | 多条件筛选 (行业/价格/涨跌幅) |
| `getCorrelation(codeA, codeB)` | GET | `/analysis/correlation` | Pearson 相关系数 |
| `getSectorRanking()` | GET | `/analysis/sector-ranking` | 行业涨跌排行 (板块云图) |

#### 基金模块

| 前端函数 | HTTP | 后端端点 | 说明 |
|:---------|:----:|:---------|:-----|
| `getFundList()` | GET | `/fund/list` | 基金分页列表 |
| `getFundInfo(code)` | GET | `/fund/{code}` | 基金详情 |
| `getFundNav(code)` | GET | `/fund/{code}/nav` | 基金净值历史 |
| `getFundHoldings(code)` | GET | `/fund/{code}/holdings` | 基金持仓 |

#### 信号模块

| 前端函数 | HTTP | 后端端点 | 说明 |
|:---------|:----:|:---------|:-----|
| `getHotReason(date)` | GET | `/signal/hot-reason` | 题材归因 |
| `getDragonTigerDaily(date)` | GET | `/signal/dragon-tiger/daily` | 龙虎榜 |
| `getNorthboundLatest(days)` | GET | `/signal/northbound/latest` | 北向资金 |
| `getLockupByStock(code)` | GET | `/signal/lockup/stock/{code}` | 限售解禁 |
| `getIndustryCompare(date)` | GET | `/signal/industry-compare` | 行业对比 |

#### 用户/自选模块

| 前端函数 | HTTP | 后端端点 | 说明 |
|:---------|:----:|:---------|:-----|
| `login(username, pwd)` | POST | `/user/login` | 登录→JWT Token |
| `register(data)` | POST | `/user/register` | 注册 |
| `getUserInfo()` | GET | `/user/info` | 用户信息 |
| `getWatchlist(userId)` | GET | `/watchlist/{userId}` | 自选列表 |
| `addWatchlist(...)` | POST | `/watchlist/add` | 添加自选 |
| `removeWatchlist(...)` | DELETE | `/watchlist/remove` | 移除自选 |

#### AI 对话

| 前端函数 | HTTP | 后端端点 | 说明 |
|:---------|:----:|:---------|:-----|
| `chatAI(data)` | POST | `/ai/chat` | AI 对话 (通过 Nginx → AI 服务) |
| `getAIStatus()` | GET | `/ai/status` | AI 服务状态 |

### 5.2 AI 服务 → 后端 API (服务间调用)

```
AI Service (FastAPI)
       │
       ├── DialogueService._build_context(stock_code)
       │     └── httpx GET {backend_api_url}/api/stock/{code}         (行情)
       │         httpx GET {backend_api_url}/api/analysis/technical/{code} (技术指标)
       │         httpx GET {backend_api_url}/api/signal/overview/{code}    (市场信号)
       │
       └── BaseAgent._fetch_backend_data(endpoint)
             └── httpx GET {backend_api_url}/{endpoint}  (各 Agent 按需调用)
```

### 5.3 认证机制

```
用户登录
  │
  POST /api/user/login {username, password}
  │
  ▼
UserController.login()
  ├── UserService.authenticate(username, password) → BCryptPasswordEncoder.matches()
  ├── JwtUtil.generateToken(userId, username) → eyJhbGci...
  └── 返回 {token: "eyJ...", user: {...}}
         │
         ▼
  前端 localStorage.setItem("token", token)
         │
         ▼
  后续所有请求:
    Axios 拦截器: headers.Authorization = "Bearer eyJ..."

  Nginx → Backend JwtFilter (OncePerRequestFilter)
     ├── 白名单路径 (/user/login, /user/register, /swagger-ui/**, /v3/api-docs/**)
     │     └── 直接放行
     │
     └── 其他路径:
           ├── 解析 Authorization Header
           ├── JwtUtil.validateToken(token)
           ├── 设置 SecurityContextHolder
           └── 放行到 Controller

  Token 过期 (24h):
     ├── JwtFilter → 返回 401
     ├── Axios 响应拦截器捕获 401
     └── localStorage.removeItem("token") → 跳转 /login
```

---

## 6. 核心模块详解

### 6.1 前端模块 (Vue 3 SPA)

**技术栈**: Vue 3 + TypeScript + Pinia + Vue Router + ECharts + Element Plus

**页面路由** (18 个视图):

| 路由路径 | 视图组件 | 功能 |
|:---------|:---------|:-----|
| `/home` | `HomeView.vue` | 首页大盘 (指数轮播、板块云图、资金流向) |
| `/stocks` | `StockListView.vue` | 股票列表 (搜索、行业筛选、排序、分页) |
| `/stock/:code` | `StockDetailView.vue` | 个股详情 (K线、技术指标、缠论、AI分析) |
| `/portfolio` | `PortfolioView.vue` | 持仓管理 |
| `/watchlist` | `WatchlistView.vue` | 自选列表 |
| `/fund` | `FundListView.vue` | 基金列表 |
| `/fund/:code` | `FundDetailView.vue` | 基金详情 (净值、持仓) |
| `/chat` | `ChatView.vue` | AI 智能对话 |
| `/hot-reason` | `HotReasonView.vue` | 题材热点 |
| `/dragon-tiger` | `DragonTigerView.vue` | 龙虎榜 |
| `/northbound` | `NorthboundView.vue` | 北向资金 |
| `/lockup` | `LockupView.vue` | 限售解禁 |
| `/industry-compare` | `IndustryCompareView.vue` | 行业对比 |
| `/sector/:name` | `SectorDetailView.vue` | 行业详情 |
| `/index/:code` | `IndexDetailView.vue` | 指数详情 |
| `/news` | `NewsView.vue` | 实时新闻 |
| `/consensus-eps` | `ConsensusEpsView.vue` | 一致预期 |
| `/fund-flow` | `FundFlowView.vue` | 资金流向 |
| `/login` | `LoginView.vue` | 登录/注册 |

### 6.2 后端模块 (Spring Boot)

**9 个 REST Controller**:

| Controller | 路径前缀 | 核心方法 |
|:-----------|:---------|:---------|
| `StockController` | `/api/stock` | list, getByCode, getKline, search, getIndustries |
| `FundController` | `/api/fund` | list, getInfo, getNav, getHoldings |
| `AnalysisController` | `/api/analysis` | yearlyReturn, monthlyReturn, trend, filter, correlation, sectorRanking |
| `SignalController` | `/api/signal` | hotReason, dragonTiger, northbound, lockup, industryCompare |
| `UserController` | `/api/user` | login, register, getUserInfo |
| `WatchlistController` | `/api/watchlist` | getList, add, remove |
| `IndexController` | `/api/index` | list, getInfo, getKline |
| `AIController` | `/api/ai` | chat, query, status |

**安全配置** (`security/SecurityConfig.java`):
- Spring Security + JWT 无状态认证
- CSRF 禁用 (前后端分离)
- CORS 全放行 (开发阶段)
- 白名单路径: `/api/user/login`, `/api/user/register`, `/api/public/**`, Swagger UI

**Redis 缓存** (`config/RedisConfig.java`):
- `CacheManager`: TTL=30 分钟, Jackson JSON 序列化
- `@Cacheable`: 应用于股票列表、K 线数据等高频查询

**数据持久化** (MyBatis-Plus):
- `@TableName` 自动映射 16 张实体表
- `PaginationInnerInterceptor` 分页支持
- `MyMetaObjectHandler` 自动填充 `created_at` / `updated_at`
- `@Version` 乐观锁 (部分表)

### 6.3 AI 服务模块 (FastAPI)

**7 个 AI Agent**:

| Agent | 职责 | 依赖数据 |
|:------|:-----|:---------|
| `FundamentalsAnalyst` | 基本面分析 | 后端 API: PE/PB/市值/盈利 |
| `TechnicalAnalyst` | 技术分析 | 后端 API: K 线/MA/MACD/RSI/KDJ/布林带 |
| `SentimentAnalyst` | 情绪分析 | 后端 API: 题材热度/北向/主力资金 |
| `NewsAnalyst` | 新闻分析 | 后端 API: 公告/研报/新闻 |
| `ResearcherTeam` | 研究员小组 (3 轮辩论) | 综合以上数据 |
| `TraderAgent` | 交易决策 | 综合报告 → 买卖/仓位/止损 |
| `RiskManager` | 风控审核 | 交易决策 → 风险评级 → 批准/驳回 |

**3 种工作模式**:

| 模式 | 触发条件 | 行为 |
|:-----|:---------|:-----|
| **实时模式** | 配置了 `DEEPSEEK_API_KEY` | 调用 DeepSeek API, 真实 AI 分析 |
| **模拟模式** | 未配置 `DEEPSEEK_API_KEY` | 关键字匹配模板, 填充模拟数据 |
| **降级模式** | API 调用超时/异常 | 自动回退到模拟模式 |

### 6.4 数据采集模块 (Python)

**6 个数据源**:

| 采集器 | 协议 | 数据类型 | 优先级 | 稳定性 |
|:-------|:----:|:---------|:------:|:------:|
| `mootdx` | TCP :7709 | K 线/五档盘口/逐笔/F10 | 10 | ⭐⭐⭐⭐⭐ |
| `tencent` | HTTP | 实时行情/PE/PB/市值 | 9 | ⭐⭐⭐⭐ |
| `ths_hot` | HTTP | 强势股题材归因 | 8 | ⭐⭐⭐⭐ |
| `ths_northbound` | HTTP | 北向资金分钟流向 | 8 | ⭐⭐⭐⭐ |
| `baidu` | HTTP (PAE) | 概念板块/资金流向 | 7 | ⭐⭐⭐ |
| `akshare_ext` | HTTP | 龙虎榜/解禁/行业/研报 | 6 | ⭐⭐ (东财反爬) |

---

## 7. 部署架构

### 7.1 容器部署拓扑

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Docker Host                                     │
│                                                                          │
│  ┌─ Layer 1: 数据采集层 (collector-net, 172.20.0.x) ──────────────────┐ │
│  │                                                                      │ │
│  │  ┌──────────────┐   ┌────────────────┐   ┌────────────────────────┐ │ │
│  │  │ collector-   │   │ collector-     │   │ data-collector         │ │ │
│  │  │ zookeeper    │──▶│ kafka          │◀──│ (Python 多源采集器)     │ │ │
│  │  │ (2181)       │   │ :9092(宿主机)   │   │ 6 数据源工厂模式       │ │ │
│  │  │              │   │ 29092(采集层内)  │   │ 熔断器+限流+重试       │ │ │
│  │  └──────────────┘   │ 39092(大数据层)  │   └──────────┬─────────────┘ │ │
│  │                     └────────────────┘              │ 共享卷          │ │
│  │                       │ 双网卡桥接                    ▼                │ │
│  └───────────────────────┼────────────────────────────────────────────┘  │
│                          │ collector-data (stock-collector-data 卷)      │
│                          ▼                                               │
│  ┌─ Layer 2: 大数据层 (bigdata-net, 172.19.0.x) ──────────────────────┐ │
│  │                                                                      │ │
│  │  ┌─ Tier 3: 应用服务 ────────────────────────────────────────────┐  │ │
│  │  │  ┌────────────┐ ┌──────────────┐ ┌────────────┐              │  │ │
│  │  │  │ Frontend    │ │   Backend    │ │ AI Service │              │  │ │
│  │  │  │ (Nginx :80) │ │ (Spring     │ │ (FastAPI   │              │  │ │
│  │  │  │             │ │  :8082)     │ │  :8000)    │              │  │ │
│  │  │  └────────────┘ └──────┬───────┘ └────────────┘              │  │ │
│  │  └────────────────────────┼─────────────────────────────────────┘  │ │
│  │                           │                                         │ │
│  │  ┌─ Tier 1: 基础设施存储 ─┼──────────────────────────────────────┐  │ │
│  │  │  ┌────────────┐ ┌──────┴───────┐ ┌──────────────────────┐    │  │ │
│  │  │  │ MySQL 8.0   │ │   Redis 7    │ │ HDFS:                │    │  │ │
│  │  │  │ (3306)      │ │   (6379)     │ │  NameNode(9870)      │    │  │ │
│  │  │  │ 16 张业务表  │ │   TTL=30min  │ │  DataNode1(9864)    │    │  │ │
│  │  │  └────────────┘ └──────────────┘ │  DataNode2           │    │  │ │
│  │  │                                   └──────────────────────┘    │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  │                                                                     │ │
│  │  ┌─ Tier 2: 大数据计算引擎 ──────────────────────────────────────┐  │ │
│  │  │  ┌────────────┐ ┌──────────────┐ ┌────────────────────────┐  │  │ │
│  │  │  │ YARN       │ │ Hive Server2 │ │ Spark Master(:8080)   │  │  │ │
│  │  │  │ RM(:8088)  │ │ (10000/10002)│ │ Spark Worker(:8081)   │  │  │ │
│  │  │  │ NM         │ │ ORC格式优化表 │ │ 共享 spark_config 模块 │  │  │ │
│  │  │  └────────────┘ └──────────────┘ └────────────────────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  宿主机端口映射:                                                          │
│    80    ← Frontend (Nginx)                                               │
│    9870  ← HDFS NameNode WebUI                                            │
│    8088  ← YARN RM WebUI                                                  │
│    8080  ← Spark Master WebUI                                             │
│    8081  ← Spark Worker WebUI                                             │
│    10002 ← Hive WebUI                                                     │
│    3306  ← MySQL                                                          │
│    6379  ← Redis                                                          │
│    9092  ← Kafka (采集层, 仅调试用)                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 监控服务

| 服务 | 容器名 | 镜像 | 端口 | 用途 |
|:-----|:-------|:-----|:----:|:-----|
| **Prometheus** | `prometheus` | `prom/prometheus:v2.51.0` | 9090 | 指标采集 (15s间隔, 30天保留) |
| **Grafana** | `grafana` | `grafana/grafana:10.4.2` | 3000 | 可视化仪表板 (admin/admin) |

| AI 记忆持久化 | Redis(已支持) | Docker 内 Redis 服务 | 故障时自动回退文件系统 |

### 7.2 容器清单 (16 个容器, 分两层部署, 含监控)

> ⚡ 较上版本新增: Prometheus + Grafana (监控)、Hive UDF 模块、Spark MLlib 模块

#### Layer 1: 数据采集层 (独立 `collector-net`)

| 服务 | 容器名 | 镜像 | CPU/Mem | 端口 | 网络 |
|:-----|:-------|:-----|:-------:|:----:|:----:|
| **Zookeeper** | `collector-zookeeper` | `cp-zookeeper:7.5.0` | 0.5C/512M | 2181 | collector-net |
| **Kafka** | `collector-kafka` | `cp-kafka:7.5.0` | 1C/1G | 9092/29092/39092 | collector-net + bigdata-net |
| **Data Collector** | `data-collector` | 自构建 (Python 3.11) | 1C/1G | - | collector-net |

#### Layer 2: 大数据层 (共享 `bigdata-net`)

| **服务** | **容器名** | **镜像/Dockerfile** | **CPU/Mem** | **端口** | **Tier** |
|:---------|:-----------|:--------------------|:-----------:|:--------:|:--------:|
| Frontend  | `frontend`   | 自构建 (Nginx)     | 0.5C/256M  | 80        | 应用服务 |
| Backend   | `backend`    | 自构建 (Java 17)   | 2C/2G      | 8082      | 应用服务 |
| AI Service| `ai-service` | 自构建 (Python 3.11)| 4C/4G     | 8000      | 应用服务 |
| MySQL     | `mysql`      | `mysql:8.0`        | 2C/2G      | 3306      | 基础设施存储 |
| Redis     | `redis`      | `redis:7-alpine`   | 0.5C/256M  | 6379      | 基础设施存储 |
| NameNode  | `namenode`   | `hadoop-namenode:2.0.0` | 2C/2G | 9870      | 基础设施存储 |
| DataNode1 | `datanode1`  | `hadoop-datanode:2.0.0` | 2C/2G | 9864      | 基础设施存储 |
| DataNode2 | `datanode2`  | `hadoop-datanode:2.0.0` | 2C/2G | -         | 基础设施存储 |
| RM        | `resourcemanager` | `hadoop-resourcemanager:2.0.0` | 1C/1G | 8088 | 计算引擎 |
| NM        | `nodemanager1` | `hadoop-nodemanager:2.0.0` | 2C/2G | - | 计算引擎 |
| Hive      | `hive-server` | `hive:2.3.2`       | 2C/2G      | 10000/10002 | 计算引擎 |
| SparkMaster| `spark-master` | `apache/spark:3.5.0` | 1C/1G | 8080/7077 | 计算引擎 |
| SparkWorker| `spark-worker` | `apache/spark:3.5.0` | 4C/4G | 8081      | 计算引擎 |
| Prometheus | `prometheus` | `prom/prometheus:v2.51.0` | 1C/512M | 9090 | 监控 |
| Grafana    | `grafana`    | `grafana/grafana:10.4.2` | 1C/256M | 3000 | 监控 |

---

## 8. 部署环境与配置

### 8.1 硬件/系统要求

| 项目 | 最低配置 | 推荐配置 |
|:-----|:---------|:---------|
| CPU | 4 核 | 8 核+ |
| 内存 | 16 GB | 32 GB+ |
| 磁盘 | 100 GB SSD | 256 GB+ SSD |
| Docker | 20.10+ | 24.0+ |
| Docker Compose | v2+ | v2.23+ |
| 操作系统 | Linux (Ubuntu 20.04+) / Windows 10+ | Linux (Ubuntu 22.04+) |

### 8.2 基础设施服务

| 基础设施 | 作用 | 关键配置 |
|:---------|:-----|:---------|
| **Docker Engine** | 容器运行时 | ≥ 20.10 |
| **Docker Compose** | 容器编排 | ≥ v2 |
| **Nginx** | 反向代理 + 静态资源托管 | 见 `docker/frontend/nginx.conf` |
| **MySQL 8.0** | 业务数据库 | 数据库: `stock_analysis`, 用户: `root`, 密码: `hadoop123` |
| **Redis 7** | 缓存 (30 分钟 TTL) | 默认端口 6379, 无认证 |
| **HDFS** | 分布式文件系统 | 3 副本, 256MB 块, NameNode 端口 9000 |
| **YARN** | 资源调度 | RM 端口 8088, NM 内存 2G |
| **Hive** | 数据仓库 | MySQL Metastore, Server2 端口 10000 |
| **Spark** | 分布式计算 | Master 端口 7077, Worker 内存 2G, 2 核 |

### 8.3 环境变量配置

#### AI 服务 (`ai-service/.env`)

```bash
# 服务监听
AI_SERVICE_HOST=0.0.0.0
AI_SERVICE_PORT=8000

# DeepSeek API (可选, 不配则使用模拟模式)
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_MODEL=deepseek-chat

# Kimi API (可选)
KIMI_API_KEY=
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions

# 后端服务地址 (Docker 内网)
BACKEND_API_URL=http://backend:8082/api
```

#### 后端 (`application.yml`)

```yaml
server:
  port: 8082

spring:
  datasource:
    url: jdbc:mysql://mysql:3306/stock_analysis?serverTimezone=Asia/Shanghai
    username: root
    password: hadoop123
  redis:
    host: redis
    port: 6379

ai:
  service:
    url: http://ai-service:8000
```

### 8.4 持久化数据卷

#### Layer 1: 采集层命名卷

| 卷名 | 用途 |
|:-----|:-----|
| `stock-collector-kafka-data` | Kafka 消息持久化 |
| `stock-collector-data` | 采集 CSV 原始数据 (跨层桥接到 NameNode :ro) |
| `stock-collector-logs` | 采集器日志 |

#### Layer 2: 大数据层命名卷

| 宿主机路径 | 容器路径 | 用途 |
|:-----------|:---------|:-----|
| `../data/hadoop/namenode` | `/hadoop/dfs/name` | HDFS 元数据 |
| `../data/hadoop/datanode1` | `/hadoop/dfs/data` | HDFS 数据块 (节点1) |
| `../data/hadoop/datanode2` | `/hadoop/dfs/data` | HDFS 数据块 (节点2) |
| `../data/mysql` | `/var/lib/mysql` | MySQL 业务数据 |
| `../data/spark/logs` | `/opt/spark/logs` | Spark 日志 |
| `../data/spark/worker-logs` | `/opt/spark/logs` | Spark Worker 日志 |

#### 跨层桥接卷

| 卷名 | 源 | 目标 | 访问模式 | 用途 |
|:-----|:--:|:----:|:--------:|:-----|
| `stock-collector-data` | 采集层 (collector-net) | NameNode (bigdata-net) | `ro` | CSV 批量导入 HDFS |

### 8.5 端口分配

| 宿主机端口 | 容器端口 | 服务 | 所属层 | 用途 |
|:----------:|:--------:|:-----|:------:|:-----|
| 80 | 80 | Nginx | 大数据层 | 前端访问入口 |
| 8082 | 8082 | Spring Boot | 大数据层 | REST API |
| 8000 | 8000 | FastAPI | 大数据层 | AI 服务 |
| 3306 | 3306 | MySQL | 大数据层 | 业务数据库 |
| 6379 | 6379 | Redis | 大数据层 | 缓存 |
| 9870 | 9870 | NameNode | 大数据层 | HDFS Web UI |
| 9864 | 9864 | DataNode1 | 大数据层 | DataNode Web UI |
| 8088 | 8088 | ResourceManager | 大数据层 | YARN Web UI |
| 10000 | 10000 | Hive | 大数据层 | HiveServer2 JDBC |
| 10002 | 10002 | Hive | 大数据层 | Hive Web UI |
| 8080 | 8080 | Spark | 大数据层 | Spark Master Web UI |
| 8081 | 8081 | Spark | 大数据层 | Spark Worker Web UI |
| 7077 | 7077 | Spark | 大数据层 | Spark Master RPC |
| 9092 | 9092 | Kafka | 采集层 | Kafka (仅宿主机调试) |
| 9090 | 9090 | Prometheus | 大数据层 | 指标采集与查询 |
| 3000 | 3000 | Grafana | 大数据层 | 监控仪表板 |

---

## 9. 部署流程

### 9.1 前置条件

```bash
# 1. 安装 Docker Engine (≥ 20.10)
# Windows: 安装 Docker Desktop
# Linux:
curl -fsSL https://get.docker.com | sh

# 2. 安装 Docker Compose v2
# Docker Desktop 自带
# Linux: sudo apt install docker-compose-plugin
```

### 9.2 构建与启动 (双层架构)

```powershell
# 进入 docker 目录
cd f:\bs\A_system\docker

# ====== 推荐: 使用分层部署脚本 ======
# 仅启动大数据层 (常用)
..\scripts\deploy-layers.ps1 -Mode up -Layer bigdata

# 启动全部 (先采集层, 后大数据层)
..\scripts\deploy-layers.ps1 -Mode up -Layer all

# ====== 或使用 start-all.sh (Linux/Mac) ======
# 大数据层
bash ../scripts/start-all.sh --bigdata-only

# 全量 (含采集层)
bash ../scripts/start-all.sh --full
```

### 9.3 手动分层部署

如果需要手动分步部署：

```powershell
cd f:\bs\A_system\docker

# ====== Step 1: 启动数据采集层 (可选) ======
docker compose -f docker-compose.collector.yml up -d
# 启动顺序: Zookeeper → Kafka → DataCollector
# 验证: docker compose -f docker-compose.collector.yml ps

# ====== Step 2: 启动大数据层 (+ 应用 + 生产配置) ======
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
# 启动顺序 (自动按依赖): namenode → datanode* → resourcemanager
#   → nodemanager → mysql → redis → hive-server → spark* → ai-service → backend → frontend

# 分层状态查看
docker compose -f docker-compose.collector.yml ps
docker compose -f docker-compose.yml ps

# 集成状态 (所有容器)
..\scripts\deploy-layers.ps1 -Mode status -Layer all

# 查看日志
..\scripts\deploy-layers.ps1 -Mode logs -Layer collector
..\scripts\deploy-layers.ps1 -Mode logs -Layer bigdata
```

### 9.4 MySQL 初始化

MySQL 容器首次启动时会自动执行 `docker/mysql/init.sql`，包含：

- 创建 `stock_analysis` 数据库
- 创建 **16 张业务表**: `user`, `stock`, `stock_daily`, `fund`, `fund_nav`, `fund_holding`, `market_index`, `index_daily`, `watchlist`, `signal_hot_reason`, `signal_dragon_tiger`, `signal_northbound`, `signal_lockup`, `signal_daily_industry`, `analysis_result`, `ai_chat`
- 插入 **示例数据**: 2 个测试用户 (admin/test)、20 只股票、10 只基金、100 条 K 线、25 条持仓等

### 9.5 Nginx 反向代理配置

```nginx
# docker/frontend/nginx.conf
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;      # SPA 路由支持
    }

    location /api/ {
        proxy_pass http://backend:8082/api/;   # 后端 API 代理
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ai/ {
        proxy_pass http://ai-service:8000/;    # AI 服务代理
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 9.6 数据采集

Docker 部署后数据采集自动运行（容器化）：

```powershell
# ====== 方式一: Docker 容器采集 (推荐) ======
docker compose -f docker-compose.collector.yml up -d
# data-collector 容器自动启动, 内部运行 market_collect.py

# 查看采集日志
docker logs -f data-collector

# 采集数据导入 HDFS (从共享卷)
docker exec namenode bash -c "
  hdfs dfs -put -f /data/collector_output/*.csv /user/hadoop/stock_data/daily/
"

# ====== 方式二: 宿主机直接采集 (开发调试) ======
cd f:\bs\A_system\data-collector\scheduler
pip install pandas requests akshare mootdx
python market_collect.py --all --sync
```

### 9.7 大数据批处理 (v2 优化版)

```powershell
cd f:\bs\A_system\bigdata-processing\batch

# ====== 基本用法 ======
# 全量跑批 (Hive DML + Spark batch + 数据质量检查)
python run_batch_pipeline.py --mode daily

# 指定日期增量
python run_batch_pipeline.py --mode incremental --date 2026-05-13

# ====== 高级选项 ======
# 并行执行 Spark Job (最多3个同时跑)
python run_batch_pipeline.py --mode daily --parallel

# 仅 Spark (跳过 Hive)
python run_batch_pipeline.py --mode daily --skip-hive

# 预览执行计划 (不实际运行)
python run_batch_pipeline.py --mode daily --dry-run

# ====== Hive ORC 格式迁移 ======
# 查询性能提升 5~15 倍
cd ..\scripts
python migrate_hive_to_orc.py --dry-run    # 预览迁移计划
python migrate_hive_to_orc.py              # 执行全量迁移
python migrate_hive_to_orc.py --switch     # 迁移后切换表名

# ====== HDFS 备份 ======
cd ..\backup
python hdfs_backup.py --mode full           # 全量备份 (并行导出)
python hdfs_backup.py --mode incremental --days 7  # 增量备份
python hdfs_backup.py --mode cleanup --retention-days 30  # 清理过期
```

### 9.8 停止与清理

```powershell
# ====== 推荐: 使用分层脚本 ======
..\scripts\deploy-layers.ps1 -Mode down -Layer all

# ====== 手动停止 (分层) ======
cd f:\bs\A_system\docker

# 停止大数据层 (先停, 释放依赖)
docker compose down

# 停止采集层 (后停)
docker compose -f docker-compose.collector.yml down

# 停止并删除数据卷 (数据丢失!)
docker compose down -v
docker compose -f docker-compose.collector.yml down -v

# 停止单个服务
docker compose stop backend
docker compose rm backend
```

---

## 10. 运行验证

### 10.1 一键验证

```bash
python scripts/e2e_verify.py
```

端到端验证脚本自动检查 11 项内容:
1. ✅ 项目结构完整性 (7 个必需目录)
2. ✅ Python 核心依赖 (pandas, numpy)
3. ✅ 数据源工厂 (6 个数据源)
4. ✅ 分析算法模块 (缠论分型 + 技术指标)
5. ✅ 后端 API 可达性 (localhost:8080)
6. ✅ TypeScript 编译 (vue-tsc --noEmit)
7. ✅ HDFS 连接 (可选)
8. ✅ Hive 表验证 (可选)
9. ✅ AI 服务模块文件完整性
10. ✅ 后端 AI 控制器
11. ✅ 前端 AI 对话页面

### 10.2 手动验证

```powershell
# 1. 访问前端
curl http://localhost

# 2. 测试后端 API 健康检查
curl http://localhost:8082/api/stock/list?page=1&size=5

# 3. 测试 AI 服务
curl http://localhost:8000/health

# 4. 测试 AI 对话
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"分析 600519","stock_code":"600519"}'

# 5. 验证 HDFS
docker exec namenode hdfs dfs -ls /

# 6. 验证 MySQL
docker exec mysql mysql -uroot -phadoop123 \
  -e "USE stock_analysis; SELECT COUNT(*) as stocks FROM stock;"

# 7. 验证 Hive
docker exec hive-server /opt/hive/bin/beeline \
  -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;"

# 8. 验证 Spark
docker exec spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --class org.apache.spark.examples.SparkPi \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 10
```

### 10.3 Web UI 访问

| 服务 | 访问地址 | 所属层 |
|:-----|:---------|:------:|
| 前端应用 | http://localhost | 大数据层 (app) |
| Prometheus   | http://localhost:9090 | 大数据层 (monitoring) |
| Grafana      | http://localhost:3000 | 大数据层 (monitoring) |
| HDFS WebUI | http://localhost:9870 | 大数据层 (storage) |
| YARN WebUI | http://localhost:8088 | 大数据层 (computation) |
| Hive WebUI | http://localhost:10002 | 大数据层 (computation) |
| Spark Master | http://localhost:8080 | 大数据层 (computation) |
| Spark Worker | http://localhost:8081 | 大数据层 (computation) |
| Swagger API | http://localhost:8082/swagger-ui/index.html | 大数据层 (app) |
| Prometheus   | http://localhost:9090 | 大数据层 (monitoring) |
| Grafana      | http://localhost:3000 | 大数据层 (monitoring) |

### 10.4 验证大数据层批处理

```powershell
# 验证 Hive ORC 表
python bigdata-processing\scripts\migrate_hive_to_orc.py --dry-run

# 执行批处理 (dry-run 模式预览)
python bigdata-processing\batch\run_batch_pipeline.py --mode daily --dry-run

# 验证数据质量模块
python -c "from bigdata_quality import DataQualityChecker; print('QC模块就绪')"

# 验证 Spark 共享配置
python -c "from spark_config import create_spark_session; print('Spark共享模块就绪')"

# 验证 HDFS 备份管道
python bigdata-processing\backup\hdfs_backup.py --mode list
```

### 10.5 账户凭据

> ⚠️ **安全更新 (2026-05-18)**: 凭据文件已从 `backend/src/main/resources/security/` 迁移至 `docs/security/`，**不再打包进 JAR**。生产环境请通过环境变量注入凭据。

所有账户及基础设施凭据统一参考 `docs/security/` 目录。

#### 应用用户

| 用户名 | 密码 | 角色 | 层级 |
|:-------|:-----|:-----|:----:|
| `superadmin` | `Super@Admin2026!` | 超级管理员 | L4 |
| `admin` | `Admin@Stock2026!` | 管理员 | L3 |
| `data_operator` | `DataOp@2026Sys` | 管理员 | L3 |
| `premium_trader` | `Trader@2026Pro!` | 高级用户 | L2 |
| `li_si` | `LiSiTrader@2026` | 高级用户 | L2 |
| `test` | `Test1234` | 普通用户 | L1 |
| `zhang_san` | `ZhangSan2026!` | 普通用户 | L1 |

#### Docker 基础设施凭据

| 服务 | 用户名 | 密码 | 端口 |
|:-----|:-------|:-----|:----:|
| MySQL (Docker) | `root` | `hadoop123` | 3307→3306 |
| MySQL (本地开发) | `root` | `123456` | 3306 |
| Redis | 无认证 | - | 6379 |
| JWT Secret | - | `DefaultSecretKeyForAStockSystem2026DevEnvironment` | - |

---

## 11. 开发指南

### 11.1 本地开发环境

```powershell
# ====== 后端 (需先启动 MySQL 和 Redis) ======
cd backend
mvn spring-boot:run
# 访问 http://localhost:8082/swagger-ui/index.html

# ====== 前端 ======
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000

# ====== AI 服务 ======
cd ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs (FastAPI Swagger)
```

### 11.2 本地开发配置差异

本地开发时，`frontend/vite.config.ts` 使用 Vite 代理替代 Nginx：

```typescript
// frontend/vite.config.ts
server: {
    port: 3000,
    proxy: {
        '/api': {
            target: 'http://localhost:8082',  // → 本地后端
            changeOrigin: true,
        },
    },
},
```

本地 MySQL 连接使用 `localhost:3306` (而非 Docker 内网的 `mysql:3306`)，对应 `application.yml` 中的 `spring.profiles.active: dev` 配置（默认 dev profile 使用 localhost）。

## 12. CI/CD 与监控

### 12.1 GitHub Actions 流水线

项目已配置 GitHub Actions CI 流水线 (`.github/workflows/ci.yml`)，自动执行以下任务：

| 阶段 | 触发条件 | 执行内容 |
|:-----|:---------|:---------|
| **Backend Build & Test** | push/PR | JDK 17 + Maven 编译 + 单元测试 |
| **Frontend Build & Lint** | push/PR | Node 20 + npm ci + vue-tsc 类型检查 + vite 构建 + vitest 测试 |
| **AI Service Lint & Test** | push/PR | Python 3.11 + ruff lint + pytest |
| **Docker Image Build** | 以上全部通过 | 构建 AI/Backend/Frontend 三个 Docker 镜像（cache: gha） |

```yaml
# 流水线状态:
# [![CI](https://github.com/your-org/A_system/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/A_system/actions/workflows/ci.yml)
```

### 12.2 监控系统

Prometheus + Grafana 集成在 Docker Compose 中（`docker-compose.yml`），启动后自动可用：

```
Prometheus → 采集 6 个目标（自身 / Backend / AI / Redis / MySQL / Spark）
                 │
                 ▼
Grafana    ← 预配置 Prometheus 数据源，自动加载仪表板
                 │
                 ▼
Web UI:    http://localhost:9090 (Prometheus)
           http://localhost:3000 (Grafana, admin/admin)
```

### 11.3 项目代码量统计

| 模块 | 语言 | 文件数 | 代码行数 | 备注 |
|:-----|:-----|:------:|:--------:|:-----|
| data-collector | Python | ~55 | ~3,000 | 8采集器 + 7适配器 + 管道 + 调度器 |
| bigdata-processing | SQL/Python | ~30 | ~3,500 | 7 DDL + 8 DML + 6 Spark + UDF + MLlib |
| analysis-algorithms | Python | ~22 | ~2,500 | 技术指标 + 缠论 + 量化策略 |
| backend | Java | ~100 | ~4,500 | 7 Controller + 15 Service + 28 Entity + JWT |
| frontend | Vue/TS | ~55 | ~2,500 | 20 视图 + 11 API + 4 Store + ECharts |
| ai-service | Python | ~20 | ~2,200 | 7 Agent + FusionEngine + Redis记忆 |
| docker | 多语言 | ~42 | ~2,000 | 16 服务编排 + 监控 + 7 Dockerfile |
| scripts | 多语言 | ~14 | ~1,000 | 部署脚本 + e2e验证 + 健康检查 |
| **总计** | | **~270** | **~20,000** | |

---

> **注意**: 本项目代码仅供学习参考，不构成任何投资建议。投资有风险，入市需谨慎。
>
> **License**: MIT License - Copyright (c) 2026 A_system
