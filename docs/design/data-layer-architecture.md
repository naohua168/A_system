# 数据层架构规范

> 版本: v3.0 | 更新时间: 2026-06-01

## 核心原则

**所有市场数据来自大数据层，MySQL 只保留业务数据。**

## 数据更新策略 (TTL)

| 层级 | TTL | 数据 | 刷新方式 |
|:-----|:----|:-----|:---------|
| **价格高频** (TTL_SHORT) | **1 小时** | stock_basic(price/changePct), detail_*, sector_ranking | auto_seed 每次运行强制覆盖(`safe_write_force_price`) |
| **动态信号** (TTL_MEDIUM) | **24 小时** | northbound, hot_reason, cls_news, global_news, fund_nav | auto_seed 检查 TTL>600 后跳过，自然过期后更新 |
| **静态基础** (TTL_LONG) | **7 天** | index_list, industry_compare, industry_treemap, fund_list | 首写后几乎不变，过期后自动补充 |

auto_seed.py 每 **20 分钟**运行一次，价格数据每次都会刷新，确保 Redis 中的实时价格不滞后超过 20 分钟。

## 数据分层与存储职责

| 层 | 存储 | 数据类型 | 写入者 | 读取者 |
|:---|:-----|:---------|:-------|:-------|
| **L2 大数据层** | Hive (HDFS) | 行情、K线、信号、资讯、指标 | data-collector → CSV → HDFS → Hive DDL | Spark 批处理 / hive_to_redis |
| **L2 缓存层** | Redis | 行情、K线、信号、资讯（camelCase JSON） | hive_to_redis.py / auto_seed.py | backend API (RedisReader) |
| **L4 业务层** | MySQL | user, watchlist, ai_chat, analysis_result | backend service | backend API (Mapper) |

## 数据流图

```
[外部数据源] → L1 采集器 (data-collector)
  ├→ CSV → HDFS → Hive (大数据原始仓库)
  ├→ CSV → MySQL [已废弃 · 仅兼容保留]
  └→ Kafka → Spark Streaming → Hive (实时流)

Hive → [Spark 批处理] → Hive (结果表)
     → [hive_to_redis.py] → Redis (camelCase JSON, 分级TTL)
     → [auto_seed.py / CSV→Redis] → Redis (自愈兜底)

Backend Spring Boot:
  MarketController / IndexController / SignalDataController / InfoController
  → RedisReader.get("market:stock_basic|kline_{code}|hot_reason|...")
  → 命中 → 返回
  → 未命中 → RedisCacheService.getOrFetch() → Hive JDBC 回查 → SETEX

前端 API 代理:
  /api/* → backend:8082 (Redis优先)
  /api/analysis/* → chanlun_server:8899 (缠论直读Redis)
```

## Redis Key 命名规范

```
market:stock_basic      全市场股票列表 + 价格 + PE/PB
market:detail_{code}    个股详情
market:kline_{code}     个股日K线 (最近2年)
market:index_kline_{code} 指数日K线
market:hot_reason       当日热点题材
market:northbound       北向资金
market:industry_compare 行业对比
market:sector_ranking   板块排行
market:sector_kline_{industry} 板块K线
market:fund_flow_{code} 个股资金流向
market:dragon_tiger     龙虎榜
market:lockup_{code}    限售解禁
market:concept_blocks_{code} 概念板块
market:cls_news         财联社快讯
market:global_news      全球资讯
market:fund_list        基金列表
market:fund_nav         基金净值
market:etf_list         ETF列表
market:index_list       大盘指数列表
market:max_date         最新交易日
market:industries       行业列表
```

## 禁用规则

以下 MySQL 表**仅用于业务数据，不再作为市场数据查询来源**：

| 表 | 状态 | 替代数据源 |
|:---|:-----|:-----------|
| `stock` | 只写入，不读取 | Redis `market:stock_basic` |
| `stock_daily` | 只写入，不读取 | Redis `market:kline_{code}` |
| `market_index` | 只写入，不读取 | Redis `market:index_list` |
| `index_daily` | 只写入，不读取 | Redis `market:index_kline_{code}` |
| `signal_*` | 只写入，不读取 | Redis `market:*` |
| `info_*` | 保留读写 | Redis 缓存优先 |
| `fund_*` | 保留读写 | Redis 缓存优先 |
| `user` | 业务数据，正常使用 | — |
| `watchlist` | 业务数据，正常使用 | — |
| `ai_chat` | 业务数据，正常使用 | — |
| `analysis_result` | 业务数据，正常使用 | — |

## 管道调度

| 管道 | 调度方式 | 数据源 → 目标 |
|:-----|:---------|:-------------|
| hive_to_redis.py | 每5分钟循环 | Hive HQL → Redis SETEX |
| auto_seed.py | 每20分钟 (run_collector 非交易时段) | CSV → Redis |
| run_collector.py | 循环 (交易1min/非交易30min) | 外部API → CSV + HDFS |
| sync_to_mysql.py | 仅兼容保留，不主动运行 | CSV → MySQL (已废弃) |

## 变更历史

| 日期 | 变更内容 |
|:-----|:---------|
| 2026-06-01 | v3.0 创建: 市场数据全部来自大数据层(Redis)，MySQL仅保留业务数据 |
