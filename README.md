# 基金股票智能分析系统

基于Hadoop生态系统的金融大数据分析与智能决策平台

## 项目简介

本项目是一个面向基金和股票的智能分析系统，采用Hadoop大数据技术栈，结合多源数据采集、离线计算和实时分析，为用户提供全面的金融数据分析服务。

> **当前状态**: ✅ 核心功能已开发完成（截至2026-05-08）

## 系统架构

```
[数据采集层]           →    [存储层]          →    [计算层]           →    [服务层]           →    [展示层]
data-collector               HDFS                 MapReduce               Spring Boot             Vue 3
(东方财富+Baostock+Yahoo)    Hive                 Spark                   RESTful API             ECharts
                             MySQL                缠论+技术指标                                  Element Plus
```

## 模块状态

| 模块 | 状态 | 说明 |
|:-----|:----:|:------|
| **data-collector** | ✅ | 多源数据采集: 东方财富(akshare) + Baostock + Yahoo Finance |
| **bigdata-processing** | ✅ | Hive DDL/DML + MapReduce 年收益率 + 成交量分析 + Spark 指标计算 |
| **analysis-algorithms** | ✅ | 缠论(分型→笔→线段→中枢→信号) + 技术指标(MA/MACD/KDJ/RSI/BOLL) + 量化回测 |
| **backend** | ✅ | Spring Boot CRUD API + 分析API(收益率/趋势/筛选/相关性/行业排行) |
| **frontend** | ✅ | K线图(含缠论) + 股票列表/搜索 + 基金详情 + 首页/自选/AI对话 |
| **ai-service** | 🚧 | 预留(待接入DeepSeek/Kimi API) |

---

## 开发进度 (2026-05-07 ~ 2026-05-08)

### ✅ Day 1 — 环境基石

Docker 环境 · Spring Boot 骨架 · MySQL 建表 · Vue 3 初始化

### ✅ Day 2 — 数据通道

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| T3 | **多源数据采集** | ✅ | `akshare`+`baostock`+`yfinance` 三源采集器 + 工厂模式 |
| T4 | **Hive 建表** | ✅ | 5 张表 DDL + 数据加载/分区管理/查询模板 |
| T5 | **HDFS 上传** | ✅ | 自动路由上传 + Hive MSCK REPAIR |
| T1 | 后端 CRUD API | ✅ | Stock/Fund/User/Watchlist/Analysis 接口 |
| T2 | 前端布局骨架 | ✅ | AppLayout + 路由 + 菜单 + 9 个页面 |

### ✅ Day 3 — 大数据处理

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| T1 | **MapReduce** | ✅ | 年收益率计算 + 成交量分析 |
| T2 | **Hive 分析 SQL** | ✅ | 日均价统计 + 涨跌幅排名 + 行业榜 |
| T3 | **Spark 脚本** | ✅ | 实时指标(MA/MACD/RSI) + Hive SQL 查询 |
| T4 | **后端分析 API** | ✅ | 收益率/趋势/筛选/相关性/行业排行 |

### ✅ Day 4 — 分析算法

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| T1 | **缠论** | ✅ | K线包含处理 → 分型 → 笔 → 线段 → 中枢 → 信号 |
| T2 | **可视化接口** | ✅ | JSON 序列化 + 统一分析入口 |
| T3 | **技术指标** | ✅ | MA/MACD/KDJ/RSI/BOLL (纯 Pandas 实现) |
| T4 | **量化模型** | ✅ | 策略基类 + 均线策略 + 回测引擎 |

### ✅ Day 5 — 前端冲锋

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| T1 | **K线图页面** | ✅ | ECharts K线 + MA/BOLL/MACD/KDJ/RSI + 缠论可视化 |
| T2 | **股票列表/搜索** | ✅ | 搜索筛选 + 行业过滤 + 排序 + 分页 |
| T3 | **基金页面** | ✅ | 净值走势 + 收益率卡片 + 前十大持仓 |
| T4 | **首页增强** | ✅ | 大盘指数轮播 + 板块云图 + 热门股票 |

### 🚧 Day 6 — 集成完善

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| T1 | **E2E 验证脚本** | ✅ | `scripts/e2e_verify.py` 全链路检查 |
| T2 | **启动脚本** | ✅ | `start-all.sh` / `stop-all.sh` |
| T3 | **API 文档** | ✅ | Stock / Analysis / Fund 三大模块 |
| T4 | **部署指南** | ✅ | `docs/deployment/quick-start.md` |

### ✅ Day 7 — 收尾完成

| # | 任务 | 状态 | 产出 |
|:-:|:----|:----:|:-----|
| T1 | **AI 对话服务** | ✅ | FastAPI 微服务 + 后端 Controller + 前端 ChatView（DeepSeek 协议 + 模拟降级） |
| T2 | **E2E 验证通过** | ✅ | 8 项检查 7 项通过（不含前端编译环境依赖） |
| T3 | **演示脚本** | ✅ | `docs/demo-script.md` 含 AI 对话演示环节 |

---

## 1周 → 16周 映射关系

| 1周Day | 对应16周阶段 |
|:------:|:------------|
| Day 1 | W1-W2 环境搭建 |
| Day 2 | W3-W4 数据采集 |
| Day 3 | W5-W6 大数据处理 |
| Day 4 | W7-W8 分析算法 |
| Day 5 | W9-W10 后端+前端 |
| Day 6 | W11-W14 AI服务+集成 |
| Day 7 | W15-W16 测试+文档 |

---

## 技术架构

```
├── 数据采集层: Python爬虫 + API调用
├── 大数据处理层: Hadoop + MapReduce + Spark + Hive
├── 数据存储层: HDFS + HBase + MySQL + Redis
├── 后端服务层: Spring Boot + MyBatis Plus
├── 前端展示层: Vue 3 + TypeScript + Element Plus
└── AI对话层: Python Flask/FastAPI + 多AI融合
```

## 项目目录结构

```
A_system/
├── 📁 data-collector/          # 数据采集模块 (Python)
│   ├── crawler/                # 爬虫脚本
│   ├── api/                    # API调用模块
│   ├── scheduler/              # 定时任务调度
│   └── requirements.txt        # Python依赖
│
├── 📁 bigdata-processing/      # 大数据处理模块
│   ├── mapreduce/              # MapReduce作业 (Java)
│   ├── spark/                  # Spark作业 (Python/Java)
│   ├── hive/                   # Hive数据仓库脚本
│   └── scripts/                # 数据处理脚本
│
├── 📁 backend/                 # 后端服务 (Spring Boot)
│   ├── src/                    # 源代码
│   ├── pom.xml                 # Maven配置
│   └── application.yml         # 应用配置
│
├── 📁 frontend/                # 前端应用 (Vue 3)
│   ├── src/                    # 源代码
│   ├── public/                 # 静态资源
│   ├── package.json            # NPM依赖
│   └── vite.config.ts          # Vite配置
│
├── 📁 ai-service/              # AI对话服务 (Python)
│   ├── app/                    # Flask/FastAPI应用
│   ├── models/                 # AI模型封装
│   ├── fusion/                 # 多AI结果融合算法
│   └── requirements.txt        # Python依赖
│
├── 📁 analysis-algorithms/     # 分析算法库
│   ├── chanlun/                # 缠论分析算法
│   ├── technical/              # 技术指标计算
│   └── quantitative/           # 量化分析模型
│
├── 📁 docker/                  # Docker环境配置
│   ├── hadoop/                 # Hadoop集群配置
│   ├── docker-compose.yml      # 服务编排
│   └── scripts/                # 启动脚本
│
├── 📁 docs/                    # 项目文档
│   ├── design/                 # 设计文档
│   ├── api/                    # API接口文档
│   └── deployment/             # 部署文档
│
├── 📁 data/                    # 数据目录 (Git忽略)
│   ├── raw/                    # 原始数据
│   ├── processed/              # 清洗后数据
│   └── samples/                # 示例数据
│
├── 📄 README.md                # 项目说明文档
├── 📄 CONTRIBUTING.md          # Git贡献指南
└── 📄 基金股票智能分析系统 - 毕业设计技术指导文档.md
```

## 模块说明

### 1. data-collector (数据采集)
- **职责**: 从东方财富、同花顺、新浪等数据源采集股票和基金数据
- **技术**: Python + Scrapy/Selenium + Requests
- **输出**: 原始数据写入HDFS

### 2. bigdata-processing (大数据处理)
- **职责**: 离线/实时数据处理与分析
- **技术**: MapReduce (历史分析) · Spark Streaming (实时计算) · Hive (数据仓库)
- **输出**: 分析结果存储到HBase/MySQL

### 3. backend (后端服务)
- **职责**: 提供RESTful API和WebSocket服务
- **技术**: Spring Boot + MyBatis Plus + Spring Security
- **功能**: 用户管理、行情服务、分析服务、AI对话接口

### 4. frontend (前端展示)
- **职责**: 用户界面和可视化展示
- **技术**: Vue 3 + TypeScript + Element Plus + ECharts
- **功能**: 行情展示、K线图、分析报表、AI对话界面

### 5. ai-service (AI对话服务)
- **职责**: 集成多AI提供智能对话和分析建议
- **技术**: Python Flask/FastAPI + RESTful API调用
- **功能**: 多AI结果融合、智能问答、分析建议

### 6. analysis-algorithms (分析算法)
- **职责**: 金融分析算法实现
- **技术**: Python + Pandas/NumPy + TA-Lib
- **功能**: 缠论分析、技术指标、量化模型

### 7. docker (环境配置)
- **职责**: 一键搭建Hadoop开发环境
- **技术**: Docker + Docker Compose
- **组件**: NameNode、DataNode、Hive、Spark、MySQL

## 快速开始

### 环境要求
- Docker & Docker Compose
- Java 11+
- Python 3.8+
- Node.js 16+

### 1. 启动大数据环境
```bash
cd docker
docker-compose up -d
```

### 2. 启动后端服务
```bash
cd backend
mvn spring-boot:run
```

### 3. 启动前端开发
```bash
cd frontend
npm install
npm run dev
```

### 4. 启动AI服务
```bash
cd ai-service
pip install -r requirements.txt
python app.py
```

## 主要功能

- 📊 **实时行情**: 股票/基金实时数据展示
- 📈 **K线图表**: 多种周期K线图和技术指标
- 🔍 **智能分析**: 缠论分析、趋势预测
- 🤖 **AI对话**: 多AI融合智能问答
- 📋 **自选管理**: 个性化自选股/基金跟踪
- 🔔 **预警提醒**: 价格异动、技术指标突破提醒

## 模块化与可扩展性

| 扩展点 | 设计方式 | 当前状态 |
|:-------|:---------|:---------|
| **数据源** | `BaseCollector` 抽象类 + 工厂模式 | 实现东方财富, 预留扩展 |
| **分析算法** | `Indicator` 接口 + `AlgorithmRegistry` | 缠论+5个指标, 注册机制就绪 |
| **AI服务商** | `AIProvider` 接口 + YAML配置 | 集成1个AI, 配置模板就绪 |
| **前端图表** | 组件化封装 (StockChart/IndicatorPanel) | K线+成交量+均线, 参数配置 |
| **大数据引擎** | 抽象 `DataProcessor` 接口 | MR+Hive+Spark 各一个模板作业 |

## 许可证

本项目仅供毕业设计学习使用

---

*注: 本文档随项目进展持续更新 · 最后更新: 2026-05-07*
