# 系统架构 (v5.2)

**更新**: 2026-06-11

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│  前端 (Vue 3 + ECharts · TypeScript)    localhost:5173      │
│  14 页面, REST API + WebSocket 实时推送                      │
├─────────────────────────────────────────────────────────────┤
│  后端 (Spring Boot 2.7 · Java 17)    端口 8082              │
│  RedisDataController 直读 Redis (camelCase JSON)             │
│  AnalysisController → ProcessBuilder → Python 缠论 Bridge   │
│  HistoryController → MySQL 历史复盘                           │
├─────────────────────────────────────────────────────────────┤
│  数据缓存 (Redis 7 · AOF+RDB)                                │
│  分级 TTL: 12h(个股) / 24h(信号/指数) / 7天(锁解)            │
├─────────────────────────────────────────────────────────────┤
│  数据采集 (Python 3.11)                                      │
│  auto_seed.py (socket RESP) · seed_kline.py · run_collector │
│  盘中仅新闻+北向分时 · 盘后 data_rollover() 全量更新           │
├─────────────────────────────────────────────────────────────┤
│  历史存储 (MySQL 8.0)                                        │
│  stock_daily(331k行) + 6张信号表                              │
│  每日 15:00 后 snapshot 归档                                  │
└─────────────────────────────────────────────────────────────┘
```

## 数据流

| 阶段 | 时间 | 动作 |
|:-----|:-----|:------|
| 盘中 | 09:00~15:00 | 仅刷新新闻(5min) + 北向分时(262点) |
| 收盘 | 15:00+ | `data_rollover()`: 行情冻结→信号采集→K线→MySQL归档 |
| 非交易日 | — | 无操作，展示最近交易日快照 |

## Redis Key 命名规范

```
market:stock_basic              # 个股行情 (5542只)
market:index_list               # 指数行情 (5指数)
market:northbound               # 北向资金日汇总
market:northbound_minute:YYYYMMDD  # 北向分时 (262点)
market:hot_reason               # 热点题材
market:dragon_tiger             # 龙虎榜
market:industry_compare         # 行业对比 (99行业)
market:industry_treemap         # 行业云图 (99行业)
market:analysis:top_gainers     # 涨跌排行
market:lockup_upcoming          # 限售解禁
market:kline_{code}             # 日K线
market:kline_{period}_{code}    # 分钟K线
market:index_kline_{code}       # 指数K线
market:cls_news / global_news   # 资讯
market:rollover_done_today      # 收盘快照标志
```

## 容器

| 服务 | 端口 | 依赖 |
|:-----|:----|:------|
| redis | 6379 | — |
| mysql | 3306 | — |
| backend | 8082 | redis, mysql |
| data-collector | — | redis |
| ai-service | 8000 | (可选) |
| frontend | 5173 | backend |
