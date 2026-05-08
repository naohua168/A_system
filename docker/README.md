# Docker 大数据环境配置

## 🚀 已部署服务（9个容器）

| 服务 | 镜像 | Web UI | 端口 | Health |
|:---|:---|:---:|:---:|:---:|
| **NameNode** | bde2020/hadoop-namenode:2.0.0 | 9870 | 9000 | ✅ |
| **DataNode × 2** | bde2020/hadoop-datanode:2.0.0 | 9864 | - | ✅ |
| **ResourceManager** | bde2020/hadoop-resourcemanager:2.0.0 | 8088 | - | ✅ |
| **NodeManager** | bde2020/hadoop-nodemanager:2.0.0 | - | - | ✅ |
| **MySQL 8.0** | mysql:8.0 | - | 3307 | ✅ |
| **Hive Server2** | bde2020/hive:2.3.2 | 10002 | 10000 | ✅ |
| **Spark Master** | apache/spark:3.5.0 | 8080 | 7077 | ✅ |
| **Spark Worker** | apache/spark:3.5.0 | 8081 | - | ✅ |

## 快速启动

```powershell
cd f:\bs\A_system\docker
docker compose up -d
```

## Web UI 访问

| 服务 | 地址 |
|:---|:---|
| HDFS | http://localhost:9870 |
| YARN | http://localhost:8088 |
| Hive | http://localhost:10002 |
| Spark Master | http://localhost:8080 |
| Spark Worker | http://localhost:8081 |

## 验证命令

### 1. HDFS
```powershell
docker exec namenode hdfs dfs -ls /
```

### 2. MySQL（8张业务表已创建）
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

### 5. 所有容器状态
```powershell
docker compose ps
```

## 数据库

| 数据库 | 类型 | 用途 |
|:---|:---|:---|
| `stock_analysis` | MySQL:3307 | 业务数据（8张表） |
| `metastore_db` | Derby (嵌入式) | Hive 元数据 |

### MySQL 表结构
- `user` - 用户管理
- `stock` - 股票基础信息（20只示例股票）
- `stock_daily` - 日K线数据
- `fund` - 基金基础信息（10只示例基金）
- `fund_nav` - 基金净值历史
- `watchlist` - 自选管理
- `analysis_result` - 分析结果
- `ai_chat` - AI对话记录

## 生产环境优化

- ✅ **健康检查** - 所有关键服务配置 healthcheck
- ✅ **自动重启** - restart: unless-stopped
- ✅ **持久化数据卷** - Hadoop/MySQL/Hive 数据持久化
- ✅ **Spark 实时计算** - Master + Worker 集群模式
- ✅ **Hive 数据仓库** - 嵌入式 Derby（轻量无外部依赖）

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
| 9870 | 9870 | HDFS WebUI |
| 9864 | 9864 | DataNode WebUI |
| 8088 | 8088 | YARN WebUI |
| 9000 | 9000 | HDFS RPC |
| 3307 | 3306 | MySQL（避开了本地3306） |
| 10000 | 10000 | Hive JDBC |
| 10002 | 10002 | Hive WebUI |
| 8080 | 8080 | Spark Master |
| 8081 | 8081 | Spark Worker |
| 7077 | 7077 | Spark RPC |

## 数据目录

- `../data/hadoop/` - HDFS NameNode + DataNode 数据
- `../data/mysql/` - MySQL 数据
- `../data/spark/` - Spark 日志
