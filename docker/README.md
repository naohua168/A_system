# Docker 大数据环境配置

## 🚀 已部署服务（18个容器，含基础设施+应用+采集+监控）

### 基础设施（9个）

| 服务 | 镜像 | Web UI | 端口 | Health |
|:---|:---|:---:|:---:|:---:|
| **NameNode** | bde2020/hadoop-namenode:2.0.0 | 9870 | 9000 | ✅ |
| **DataNode1** | bde2020/hadoop-datanode:2.0.0 | 9864 | - | ✅ |
| **DataNode2** | bde2020/hadoop-datanode:2.0.0 | - | - | ✅ (V2.2 新增) |
| **ResourceManager** | bde2020/hadoop-resourcemanager:2.0.0 | 8088 | - | ✅ |
| **NodeManager** | bde2020/hadoop-nodemanager:2.0.0 | - | - | ✅ |
| **MySQL 8.0** | mysql:8.0 | - | 3306 | ✅ |
| **Redis 7** | redis:7-alpine | - | 6379 | ✅ |
| **Hive Server2** | bde2020/hive:2.3.2 | 10002 | 10000 | ✅ |
| **Spark Master** | apache/spark:3.5.0 | 8080 | 7077 | ✅ |
| **Spark Worker** | apache/spark:3.5.0 | 8081 | - | ✅ |
| **Prometheus** | prom/prometheus:v2.51.0 | 9090 | - | ✅ |
| **Grafana** | grafana/grafana:10.4.2 | 3001 | - | ✅ |

## 应用服务（本地构建）

| 服务 | 镜像名称 | 端口 | 构建命令 |
|:---|:---|:---:|:---|
| **AI Service** | stock-ai-service | 8000 | `docker compose build ai-service` |
| **Backend** | stock-backend | 8082 | `docker compose build backend` |
| **Frontend** | stock-frontend | 80 | `docker compose build frontend` |

## 采集层服务（独立编排 docker-compose.collector.yml）

| 服务 | 容器名 | 端口 | Health |
|:---|:---|:---:|:---:|
| **Zookeeper** | collector-zookeeper | 2181 | ✅ |
| **Kafka** | collector-kafka | 9092/29092/39092 | ✅ |
| **Data Collector** | data-collector | — | ✅ (V2.2 新增) |

## 快速启动

```powershell
cd f:\bs\A_system\docker
docker compose up -d
```

首次启动前构建自定义镜像：
```powershell
docker compose build
```

## Web UI 访问

| 服务 | 地址 |
|:---|:---|
| HDFS | http://localhost:9870 |
| YARN | http://localhost:8088 |
| Hive | http://localhost:10002 |
| Spark Master | http://localhost:8080 |
| Spark Worker | http://localhost:8081 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001（admin/admin） |

## 验证命令

### 1. HDFS
```powershell
docker exec namenode hdfs dfs -ls /
```

### 2. MySQL（23张业务表已创建）
```powershell
docker exec mysql mysql -uroot -phadoop123 -e "USE stock_analysis; SHOW TABLES;"
```

### 3. Hive
```powershell
docker exec hive-server /opt/hive/bin/beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;"
```

### 4. Spark（测试实时计算）
```powershell
docker exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --class org.apache.spark.examples.SparkPi /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 10
```

### 5. AI 服务
```powershell
curl http://localhost:8000/health
```

### 6. 所有容器状态
```powershell
docker compose ps
```

## 数据库

| 数据库 | 类型 | 用途 |
|:---|:---|:---|
| `stock_analysis` | MySQL:3306 | 业务数据（23张表） |
| `hive_metastore` | MySQL (Hive 内部) | Hive 元数据 |

### MySQL 表结构（23张表）
- `user` - 用户管理
- `stock` - 股票基础信息（20只示例股票）
- `stock_daily` - 日K线数据
- `fund` - 基金基础信息（10只示例基金）
- `fund_nav` - 基金净值历史
- `fund_holding` - 基金持仓
- `watchlist` - 自选管理
- `analysis_result` - 分析结果
- `precomputed_result` - 预计算结果
- `ai_chat` - AI对话记录
- `market_index` - 市场指数
- `index_daily` - 指数日线
- `signal_hot_reason` - 题材归因
- `signal_dragon_tiger` - 龙虎榜
- `signal_dragon_tiger_detail` - 龙虎榜明细
- `signal_northbound` - 北向资金
- `signal_lockup` - 限售解禁
- `signal_lockup_detail` - 解禁明细
- `signal_daily_industry` - 行业每日数据
- `signal_fund_flow` - 资金流向
- `signal_concept_block` - 概念板块
- `info_research_report` - 券商研报
- `info_consensus_eps` - 一致预期
- `info_stock_news` - 个股新闻
- `info_cls_news` - 财联社快讯
- `info_global_news` - 全球资讯
- `info_filing` - 巨潮公告

## 生产环境优化

- ✅ **健康检查** - 所有关键服务配置 healthcheck
- ✅ **自动重启** - restart: unless-stopped
- ✅ **持久化数据卷** - Hadoop/MySQL/Hive 数据持久化
- ✅ **Spark 实时计算** - Master + Worker 集群模式
- ✅ **Hive 数据仓库** - 元数据存储在 MySQL
- ✅ **非 root 用户** - 所有应用容器以非 root 运行
- ✅ **构建上下文优化** - 项目根 `.dockerignore` 排除非必需文件（加速构建）
- ✅ **AI 服务修复** - pip 包安装到系统 site-packages（修复非 root 用户权限问题）
- ✅ **前端构建修复** - COPY 路径适配项目根上下文（`frontend/` 前缀）

## 监控系统

### Prometheus
- 采集频率: 15s
- 数据保留: 30 天
- 采集目标: Spring Boot (actuator), AI 服务, Redis, MySQL, Spark

### Grafana
- 默认登录: `admin` / `admin`（通过环境变量覆盖）
- 数据源: 预配置 Prometheus
- 预置面板: 自动加载 `grafana/dashboards/` 目录

## 停止环境

```powershell
cd f:\bs\A_system\docker
docker compose down
```

停止并删除所有数据：
```powershell
docker compose down -v
```

## 端口说明

| 宿主机端口 | 容器端口 | 服务 |
|:---:|:---:|:---|
| 80 | 80 | Frontend (Nginx) |
| 9870 | 9870 | HDFS WebUI |
| 9864 | 9864 | DataNode WebUI |
| 8088 | 8088 | YARN WebUI |
| 9000 | 9000 | HDFS RPC |
| 8000 | 8000 | AI Service (FastAPI) |
| 8082 | 8082 | Backend (Spring Boot) |
| 3306 | 3306 | MySQL |
| 6379 | 6379 | Redis |
| 10000 | 10000 | Hive JDBC |
| 10002 | 10002 | Hive WebUI |
| 8080 | 8080 | Spark Master |
| 8081 | 8081 | Spark Worker |
| 7077 | 7077 | Spark RPC |
| 9090 | 9090 | Prometheus |
| 3001 | 3000 | Grafana |

## 数据目录

- `../data/hadoop/` - HDFS NameNode + DataNode 数据
- `../data/mysql/` - MySQL 数据
- `../data/spark/` - Spark 日志

---

## 🛠️ 开发环境（热重载模式）

### 架构说明

开发环境使用 **docker-compose override** 模式：基础设施服务（Hadoop/Hive/Spark/MySQL/Redis）复用生产配置，应用服务（backend/frontend/ai-service）替换为带热重载的开发版本。

```
┌────────────────────────────────────────────────────────────┐
│                     docker-compose.dev.yml                  │
│                                                            │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────────┐   │
│  │  backend-dev │   │ frontend-dev │   │  ai-service-dev│  │
│  │ Spring Boot  │   │  Vite HMR    │   │ uvicorn --reload│ │
│  │ devtools     │   │  WebSocket   │   │  watchfiles    │  │
│  │ JDWP:5005    │   │  poll:1s     │   │  inotify       │  │
│  └──────┬───────┘   └──────┬───────┘   └───────┬─────────┘  │
│         │                  │                    │            │
│         └──────────────────┼────────────────────┘            │
│                            │                                 │
│  ┌─────────────────────────▼─────────────────────────────┐  │
│  │             基础设施 (复用 docker-compose.yml)          │  │
│  │  HDFS · YARN · Hive · Spark · MySQL · Redis           │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 热重载机制

| 服务 | 技术 | 检测方式 | 重启延迟 | 状态保持 |
|:-----|:-----|:---------|:--------:|:--------:|
| **Backend** | spring-devtools | 轮询 target/ 目录 (2s) | ~3-5s | ✅ |
| **Frontend** | Vite HMR | WebSocket + 文件系统事件 | <1s | ✅ (模块级) |
| **AI Service** | uvicorn --reload | watchfiles (inotify) | <1s | ❌ (进程重启) |

### 文件挂载映射

宿主机路径                           → 容器内路径                 用途
-----------------------------------   -----------------------   -------------------------
`../ai-service/`                      → `/app`                   Python 源码（实时同步）
`../backend/src/`                     → `/app/src`               Java 源码（devtools 监控）
`../backend/pom.xml`                  → `/app/pom.xml`           Maven 依赖配置
`../frontend/`                        → `/app`                   Vue 源码（Vite HMR）
`stock-maven-repo` (命名卷)           → `/root/.m2`              Maven 缓存（加速构建）
`stock-maven-target` (命名卷)         → `/app/target`            编译输出缓存

### 启动开发环境

```powershell
# 1. 进入 docker 目录
cd f:\bs\A_system\docker

# 2. 构建并启动（首次需构建镜像）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 3. 查看启动状态
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps

# 4. 监控实时日志（按需跟踪特定服务）
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f ai-service
```

### 开发工作流

#### 后端开发

1. 在 IDE 中修改 Java 源代码 (`backend/src/`)
2. 文件通过 bind mount 同步到容器 `/app/src/`
3. **自动触发策略**：`spring-boot-devtools` 每 2 秒轮询一次 `target/classes` 目录
4. 检测到变化后，容器内 Spring Boot **自动重启**（约 3-5 秒）
5. 对于新增依赖（修改 pom.xml），需手动重启容器：
   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
   ```

> **提示**：如果自动重启未触发，可手动触发 Maven 增量编译：
> ```powershell
> docker exec backend-dev mvn compile -q
> ```
> devtools 检测到 `target/classes` 更新后会自动重启。

#### 前端开发

1. 在 IDE 中修改 Vue 文件 (`frontend/src/`)
2. Vite HMR 通过 WebSocket 推送增量更新到浏览器
3. **即时生效**，页面无需刷新，组件状态保持
4. 新增依赖（修改 package.json）需重启：
   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend
   ```

> ⚠️ **Docker for Windows 注意**：bind mount 的文件变更可能延迟 1-2 秒。
> 环境变量 `CHOKIDAR_USEPOLLING=1` 已配置为轮询模式解决此问题。

#### AI 服务开发

1. 在 IDE 中修改 Python 文件 (`ai-service/`)
2. `uvicorn --reload` 通过 `watchfiles` 检测变更
3. 检测到变化后 FastAPI **自动重启**（约 1 秒）
4. 安装新 Python 包后需重启：
   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.dev.yml restart ai-service
   ```

### 远程调试

后端配置了 JDWP 调试端口 `5005`，可在 IDE 中配置 Remote JVM Debug：

| IDE | 配置 |
|:----|:-----|
| **IntelliJ IDEA** | Run → Edit Configurations → Remote JVM Debug → `localhost:5005` |
| **VS Code** | launch.json 添加 `"port": 5005, "request": "attach"` |

### 验证开发环境

等待所有服务 healthcheck 通过后，访问：

| 服务 | URL | 说明 |
|:-----|:----|:-----|
| 前端 (Vite HMR) | http://localhost:5173 | 修改代码即时刷新 |
| 后端 API | http://localhost:8082/api/stock/list?page=1&size=5 | REST API |
| 后端 Swagger | http://localhost:8082/swagger-ui/index.html | API 文档 |
| AI 服务 | http://localhost:8000/health | FastAPI 健康检查 |
| AI Swagger | http://localhost:8000/docs | FastAPI 文档 |

### 停止开发环境

```powershell
# 停止并删除容器（保留数据卷）
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# 完全清理（含 Maven 缓存）
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
docker volume rm stock-maven-repo stock-maven-target
```

### 故障排查

| 现象 | 原因 | 解决 |
|:-----|:-----|:-----|
| Vite 500 错误 | 后端未就绪 | 等 backend healthcheck 通过后刷新 |
| 后端自动重启不触发 | Maven 未增量编译 | 执行 `docker exec backend-dev mvn compile` |
| 前端 HMR 不生效 | bind mount 事件延迟 | 手动刷新浏览器或等 2 秒 |
| AI 服务连接拒绝 | MySQL 未就绪 | 等 mysql healthcheck 通过 |
| Maven 构建 OOM | 容器内存不足 | docker-compose.dev.yml 中增加 `mem_limit: 4g` |
