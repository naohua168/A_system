# 基金股票智能分析系统

基于Hadoop生态系统的金融大数据分析与智能决策平台

## 项目简介

本项目是一个面向基金和股票的智能分析系统，采用Hadoop大数据技术栈，结合实时计算、数据挖掘和AI对话功能，为用户提供全面的金融数据分析服务。

> **当前状态**: MVP冲刺中 (1周冲锋计划) — 见下方开发计划

---

## 一周冲锋开发计划 (2026-05-07 ~ 2026-05-13)

本计划将16周的毕业设计开发压缩为1周高强度冲刺，采用 **MVP 优先、数据流先通** 的策略。

### 📅 Day 1 — 环境基石
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-10:00 | `docker-compose.yml` (Hadoop+Namenode+Datanode+Hive+MySQL) | 可启动环境 |
| 10:00-12:00 | 启动 Docker，验证 HDFS/Hive/MySQL 联通 | 全部容器运行中 |
| 14:00-15:00 | 生成 **Spring Boot 项目** (Maven + MyBatis Plus + Spring Web) | `backend/` 骨架 |
| 15:00-17:00 | 设计 **MySQL 数据库表** (user/stock/fund/watchlist/analysis_result) | SQL + Entity |
| 17:00-18:00 | 初始化 **Vue 3 项目** (Vite + TypeScript + Element Plus + ECharts) | `frontend/` 可运行 |

**验收**: `docker ps` 有容器 · `mvn compile` 通过 · `npm run dev` 出现页面

### 📅 Day 2 — 数据通道
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-11:00 | 东方财富/新浪API采集脚本 (Python) | 实时行情+历史K线采集 |
| 11:00-12:00 | Hive 建表 SQL (stock_basic, stock_daily_partitioned) | `hive/schema.sql` |
| 14:00-15:00 | 数据写入 HDFS + Hive 外部表关联 | 数据通道打通 |
| 15:00-17:00 | 后端 **CRUD RESTful API** (stock/fund/user/watchlist) | API可调通 |
| 17:00-18:00 | 前端 **布局骨架 + 路由 + 菜单** | 可导航管理界面 |

**验收**: `python data-collector/crawler/stock.py` 能采到数据 · API 返回 JSON

### 📅 Day 3 — 大数据处理
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-11:00 | **MapReduce**: 股票年收益率计算 | `StockYearlyReturn.java` |
| 11:00-12:00 | **Hive SQL**: 日均价、涨跌幅统计 | 分析查询脚本 |
| 14:00-16:00 | **Spark 脚本**: 实时指标计算模板 (PySpark) | `pyspark_realtime.py` |
| 16:00-18:00 | 后端 **分析API** (收益率、趋势、筛选) | 分析 Controller + Service |

**验收**: MR作业可执行输出到 HDFS

### 📅 Day 4 — 分析算法
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-11:00 | **缠论**: 分型/笔/线段/中枢识别 | `analysis-algorithms/chanlun/` |
| 11:00-12:00 | 缠论可视化接口 (JSON 输出) | 与后端对接 |
| 14:00-16:00 | **技术指标** (MA, MACD, KDJ, RSI, BOLL) | `analysis-algorithms/technical/` |
| 16:00-18:00 | **量化模型** 基础框架 (均线策略模板) | `analysis-algorithms/quantitative/` |

**验收**: 能对单只股票计算缠论分型点和常见技术指标

### 📅 Day 5 — 前端冲锋
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-12:00 | **K线图页面** (ECharts K线 + 成交量 + 均线叠加) | `StockDetail.vue` |
| 14:00-16:00 | **股票列表/搜索/自选管理** | `StockList.vue` |
| 16:00-18:00 | **基金页面** (净值走势 + 持仓分析) | `Fund/` |

**验收**: 前端展示实时K线图 · 技术指标叠画

### 📅 Day 6 — AI + 集成
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-11:00 | AI 对话服务 (Flask/FastAPI 封装 Kimi/DeepSeek API) | `ai-service/app/` |
| 11:00-12:00 | 后端 AI 对话接口 + 多AI融合逻辑 | AIService + AIController |
| 14:00-16:00 | 前端 AI 对话界面 (聊天式交互) | `Chat.vue` |
| 16:00-18:00 | **端到端数据流打通** (采集→HDFS→Hive→API→前端) | 全链路验证 |

**验收**: 输入股票代码 → K线图 + 技术指标 + AI对话

### 📅 Day 7 — 收尾
| 时间 | 任务 | 产出 |
|:---:|:---|:---|
| 09:00-12:00 | **集成测试 + Bug 修复** | 所有 URI 可访问 |
| 14:00-16:00 | **文档完善** (README, API文档, 部署文档) | `docs/` 全部文档 |
| 16:00-18:00 | **演示准备** (截图+录制) · 扩展点说明 | 演示素材 |

**验收**: 全系统端到端可用 · 文档完整

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
