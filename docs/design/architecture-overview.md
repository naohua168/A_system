# 系统架构概览

> 版本: v2.2 | 更新时间: 2026-05-20

## 六层架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│  L6 前端展示层  Vue 3 + TypeScript + Element Plus + ECharts           │
│                 19 页面, 10 组件, 56+ API 端点                         │
├────────────────────────────────────────────────────────────────────────┤
│  L5 AI 智能层   FastAPI + 7 Agent + SiliconFlow / DeepSeek            │
│                 加权融合引擎 + 记忆服务 + SSE 流式                      │
├────────────────────────────────────────────────────────────────────────┤
│  L4 后端 API    Spring Boot 2.7 + MyBatis-Plus + JWT + Redis          │
│                 10 Controller, 28 Entity, 94+ API 端点                 │
├────────────────────────────────────────────────────────────────────────┤
│  L3 算法分析    9 技术指标 + 缠论六步 + 4 量化策略 + 回测引擎         │
│                 142 测试用例全通过                                       │
├────────────────────────────────────────────────────────────────────────┤
│  L2 大数据      HDFS + Hive + Spark + Kafka + MySQL + Redis           │
│                 ORC 优化表 + 实时/批处理双管道 + 数据质量检查          │
├────────────────────────────────────────────────────────────────────────┤
│  L1 数据采集    Python 多源采集器 (7数据源, 16类型)                    │
│                 Mootdx/腾讯/同花顺/百度/新浪/AkShare/资讯              │
└────────────────────────────────────────────────────────────────────────┘
```

## 数据流

```
[外部数据源] → L1 采集器 → MySQL (业务库) + Kafka (实时流)
                                ↓
                          L2 Hive 数据仓库
                                ↓
                     ┌──── Spark 批处理 ────┐
                     │ MA/趋势/排名/相关/预测 │
                     └─────────┬────────────┘
                               ↓
                     L4 Backend REST API
                     ↙         ↓         ↘
              L3 算法分析   L5 AI 服务   L6 前端
```

## 容器拓扑

```
bigdata-net (172.19.0.0/24)
├── namenode / datanode1 / datanode2  — HDFS 分布式存储
├── resourcemanager / nodemanager1    — YARN 资源调度
├── hive-server                        — Hive 数据仓库
├── spark-master / spark-worker        — Spark 计算引擎
├── mysql (mysql_new 别名)             — MySQL 业务数据库
├── redis                              — 缓存/会话/session
├── backend                            — Spring Boot API
├── ai-service                         — FastAPI AI 服务
└── prometheus / grafana               — 监控

collector-net (独立子网)
├── collector-zookeeper
├── collector-kafka (双网卡桥接到 bigdata-net)
└── data-collector
```

## 关键技术决策

| 决策 | 选择 | 原因 |
|:-----|:-----|:-----|
| AI 模型网关 | SiliconFlow (主) → DeepSeek (备) → Mock (降级) | 三路故障转移, 零依赖可用 |
| ORC 格式 | ZLIB 压缩 + BloomFilter 索引 | 存储节省 60%, 查询加速 3x |
| 缓存策略 | Redis + Spring Cache + 前端 TTL 缓存 | 三级缓存, 15-60s TTL |
| 认证授权 | JWT + RBAC + 4 级安全层级 | 无状态, 可水平扩展 |
| 测试策略 | pytest + Vitest + JUnit 5 + MockMvc | 全栈统一, Mock 优先 |
