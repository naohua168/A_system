# 基金股票智能分析系统

基于Hadoop生态系统的金融大数据分析与智能决策平台

## 项目简介

本项目是一个面向基金和股票的智能分析系统，采用Hadoop大数据技术栈，结合实时计算、数据挖掘和AI对话功能，为用户提供全面的金融数据分析服务。

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
└── 📄 README.md                # 项目说明文档
```

## 模块说明

### 1. data-collector (数据采集)
- **职责**: 从东方财富、同花顺、新浪等数据源采集股票和基金数据
- **技术**: Python + Scrapy/Selenium + Requests
- **输出**: 原始数据写入HDFS

### 2. bigdata-processing (大数据处理)
- **职责**: 离线/实时数据处理与分析
- **技术**: 
  - MapReduce: 历史数据分析、收益率计算
  - Spark Streaming: 实时指标计算
  - Hive: 数据仓库查询
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

## 开发计划

| 阶段 | 时间 | 任务 |
|------|------|------|
| 第1-2周 | 环境搭建 | Hadoop伪分布式部署 |
| 第3-4周 | 数据采集 | 爬虫开发、数据入库 |
| 第5-6周 | 数据处理 | MapReduce/Spark作业 |
| 第7-8周 | 分析算法 | 缠论/量化分析实现 |
| 第9-10周 | 后端开发 | Spring Boot服务 |
| 第11-12周 | 前端开发 | Vue界面实现 |
| 第13-14周 | AI功能 | 多AI集成对话 |
| 第15-16周 | 论文撰写 | 毕业设计论文 |

## 主要功能

- 📊 **实时行情**: 股票/基金实时数据展示
- 📈 **K线图表**: 多种周期K线图和技术指标
- 🔍 **智能分析**: 缠论分析、趋势预测
- 🤖 **AI对话**: 多AI融合智能问答
- 📋 **自选管理**: 个性化自选股/基金跟踪
- 🔔 **预警提醒**: 价格异动、技术指标突破提醒

## 许可证

本项目仅供毕业设计学习使用

---
*注：本文档随项目进展持续更新*
