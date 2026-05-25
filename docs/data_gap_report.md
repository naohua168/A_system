# 数据层与前端展示层对比分析

## 13 张表逐项检查

| 数据库表 | 数据量 | 展示层 API 端点 | 可用状态 |
|:---------|:------:|:----------------|:--------:|
| `stock` | 5,544 行 | `/api/market/list`, `/api/market/search` | ✅ **充足** |
| `stock_daily` | 3,360 行 / 315 只 | `/api/market/kline/{code}` | ⚠️ **平均10天，前端默认60天** |
| `index_daily` | 7 行 (仅今天) | `/api/index/{code}/kline` | ❌ **仅1天，前端需要历史K线** |
| `market_index` | 11 行 | `/api/index/list` | ✅ **充足** |
| `signal_hot_reason` | 248 行 / 3 日期 | `/api/signal/hot-reason` | ✅ **足够** |
| `signal_northbound` | 262 行 (仅今天) | `/api/signal/northbound/latest` | ⚠️ **仅今天数据** |
| `signal_daily_industry` | 240 行 | `/api/signal/industry-compare` | ✅ **足够** |
| `signal_dragon_tiger_detail` | 86 行 | `/api/signal/dragon-tiger-detail` | ✅ **足够** |
| `signal_lockup_detail` | 55 行 / 6 只 | `/api/signal/lockup/stock/{code}` | ✅ **基本够用** |
| `signal_fund_flow` | 30 行 / 3 只 | `/api/signal/fund-flow/{code}` | ⚠️ **仅3只股票** |
| `signal_concept_block` | 24 行 / 6 只 | `/api/signal/concept-blocks/{code}` | ⚠️ **仅6只股票** |
| `info_cls_news` | 60 行 | `/api/info/cls-news` | ✅ **足够** |
| `info_global_news` | 400 行 | `/api/info/global-news` | ✅ **充足** |

## 优先级建议

### P0 - 必须修复（影响核心展示）

| 问题 | 影响 | 修复方案 |
|:-----|:-----|:---------|
| `index_daily` 只有1天 | 指数K线图空白 | 重新采集腾讯指数K线（可批量拉取1年数据） |
| `stock_daily` 平均10天 | 个股K线图缺少历史 | 扩展采集到60天（腾讯K线API最大支持约1年） |

### P1 - 建议补充（增强页面丰富度）

| 问题 | 影响 | 修复方案 |
|:-----|:-----|:---------|
| `signal_fund_flow` 仅3只 | 资金流向页面空白 | 批量采集更多股票（push2 API） |
| `signal_concept_block` 仅6只 | 概念板块视图空白 | 推2API连接问题已定位，扩大采集范围 |
| `signal_northbound` 仅今天 | 北向历史趋势不可见 | 采集更多历史数据 |

### P2 - 长期完善

| 问题 | 影响 | 修复方案 |
|:-----|:-----|:---------|
| 股票数 5,544（含退市） | 列表含已退市股票 | 过滤 `current_price=0` 的股票 |
