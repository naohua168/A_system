# 快速启动指南

从 git clone 到浏览器访问，5 分钟启动系统。

---

## 环境要求

| 工具 | 版本 | 用途 |
|:-----|:----:|:-----|
| Docker & Docker Compose | 最新 | 大数据环境 (Hadoop/Hive/MySQL) |
| Java | 11+ | 后端 Spring Boot |
| Maven | 3.6+ | 后端构建 |
| Python | 3.8+ | 数据采集 + 分析算法 |
| Node.js | 16+ | 前端 Vue 3 |

---

## 1. 克隆并安装依赖

```bash
git clone <repo-url>
cd A_system

# Python 依赖
cd data-collector
pip install -r requirements.txt
cd ../analysis-algorithms
pip install -r requirements.txt

# 后端
cd ../backend
mvn clean install -DskipTests

# 前端
cd ../frontend
npm install
```

---

## 2. 启动大数据环境

```bash
cd docker
docker-compose up -d

# 验证
docker ps
docker exec -it namenode hdfs dfs -ls /
```

---

## 3. 初始化 Hive 表

```bash
# 执行 Hive DDL
docker exec -it hive-server beeline -u jdbc:hive2://localhost:10000 \
  -f /opt/hive/ddl/stock_basic.sql

docker exec -it hive-server beeline -u jdbc:hive2://localhost:10000 \
  -f /opt/hive/ddl/stock_daily_partitioned.sql
```

---

## 4. 采集并上传数据

```bash
cd data-collector

# 采集示例数据
python crawler/stock_crawler.py kline 000001 --days 30

# 上传到 HDFS
python scheduler/upload_to_hdfs.py --repair
```

---

## 5. 启动后端

```bash
cd backend
mvn spring-boot:run
# 后端运行在 http://localhost:8080
```

---

## 6. 启动前端

```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
```

---

## 7. 验证

```bash
# 一键验证
python scripts/e2e_verify.py

# 浏览器打开
open http://localhost:5173
```

---

## 目录结构

```
A_system/
├── data-collector/         Python 数据采集 (多源)
├── bigdata-processing/     MapReduce + Hive + Spark
├── backend/                Spring Boot REST API
├── frontend/               Vue 3 + Element Plus
├── analysis-algorithms/    缠论 + 技术指标 + 量化
├── docker/                 Docker 环境配置
├── scripts/                运维脚本
└── docs/                   文档
```
