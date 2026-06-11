# A 股全栈量化复盘系统 · 项目总结

> 日期：2026-06-11 · 版本：v5.0

---

## 一、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (Vue 3)                        │
│  HomeView  StockDetail  IndexDetail  NorthboundView     │
│  FundFlow  Lockup  News  DragonTiger  IndustryCompare   │
│  16个视图 · Element Plus · ECharts · TypeScript         │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP REST API
┌────────────────────────▼────────────────────────────────┐
│                    后端 (Spring Boot)                     │
│  RedisDataController → RedisReader → Redis / MySQL       │
│  HistoryController   → HistoryDatasource → MySQL         │
│  SignalDataController → SignalDataService → MySQL        │
│  AnalysisController → AnalysisService → Python 缠论     │
│  17个API端点 · 30秒缓存 · 复盘日期查询                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   数据层 (Data Pipeline)                   │
│                                                          │
│  ┌─ Redis (实时展示层) ─────────────────────────────┐    │
│  │  stock_basic     index_list     northbound        │    │
│  │  hot_reason      dragon_tiger   industry_*        │    │
│  │  kline_*         fund_flow_*    lockup_upcoming   │    │
│  │  analysis:*      cls_news       global_news       │    │
│  │  northbound_minute              rollover_done_today│   │
│  └──────────────────────────────────────────────────-┘    │
│                                                          │
│  ┌─ MySQL stock_history (历史复盘层) ─────────────────┐   │
│  │  stock_daily    (331k行)  index_daily   (10行)     │   │
│  │  industry_daily (198行)  northbound_daily (2行)    │   │
│  │  hot_reason_daily(152行) dragon_tiger_daily(819行) │   │
│  │  info_news      (344行)                           │   │
│  └──────────────────────────────────────────────────-┘   │
│                                                          │
│  ┌─ 采集器 (run_collector.py + auto_seed.py) ────────┐  │
│  │  盘中: 新闻5min + 北向分时 + K线TTL检查            │   │
│  │  盘后: data_rollover() 全量更新 → MySQL归档        │   │
│  └──────────────────────────────────────────────────-┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 二、已完成的核心功能

### 2.1 数据管道 （6项）

| # | 功能 | 状态 | 说明 |
|:-:|:-----|:----:|:-----|
| 1 | 实时行情采集（5542只） | ✅ | 腾讯API → stock_basic |
| 2 | 信号数据采集（8类） | ✅ | 北向/热点/龙虎榜/行业/资金流/锁解/排行/资讯 |
| 3 | K线采集（日K+5周期分钟K） | ✅ | 日K 365天 + 分钟K 60条 |
| 4 | MySQL 归档 | ✅ | 7张表每日归档 |
| 5 | 收盘快照 rollover | ✅ | data_rollover() 4段式 |
| 6 | 数据自愈 | ✅ | K线缺失检测 + 结算延迟重试 |

### 2.2 API 端点 （17个）

| # | 端点 | 路由 | 状态 |
|:-:|:-----|:-----|:----:|
| 1 | 指数行情 | `/api/v2/index/list` | ✅ |
| 2 | 指数详情+K线 | `/api/v2/index/{code}` / `/kline` | ✅ |
| 3 | 个股列表+详情 | `/api/v2/market/list` / `/detail/{code}` | ✅ |
| 4 | 个股K线（多周期） | `/api/v2/market/kline/{code}` | ✅ |
| 5 | 北向资金 | `/api/v2/signal/northbound/latest` | ✅ |
| 6 | 北向资金分时 | `/api/v2/signal/northbound/minute` | ✅ |
| 7 | 热点题材 | `/api/v2/signal/hot-reason` | ✅ |
| 8 | 龙虎榜 | `/api/v2/signal/dragon-tiger/daily` | ✅ |
| 9 | 行业对比 | `/api/v2/signal/industry-compare` | ✅ |
| 10 | 行业云图 | `/api/v2/market/industry-treemap` | ✅ |
| 11 | 资金流向 | `/api/v2/signal/fund-flow/{code}` | ❌ (已移除) |
| 12 | 限售解禁 | `/api/v2/signal/lockup/upcoming` | ✅ |
| 13 | 涨跌排行 | `/api/v2/market/analysis/{type}` | ✅ |
| 14 | 资讯 | `/api/v2/info/cls-news` / `global-news` | ✅ |
| 15 | 缠论分析 | `/api/v2/analysis/chanlun/{code}` | ✅ |
| 16 | 历史复盘 | `/api/v2/history/*`（6个） | ✅ |
| 17 | 个股搜索 | `/api/v2/market/search` | ✅ |

### 2.3 前端页面 （14个视图）

| # | 页面 | 复盘支持 | 数据更新 |
|:-:|:-----|:--------:|:---------|
| 1 | 首页 HomeView | ✅ 日期选择 | WS实时 + 轮询 |
| 2 | 个股详情 StockDetailView | — | WS实时 |
| 3 | 指数详情 IndexDetailView | — | WS实时 |
| 4 | 股票列表 StockListView | — | 按需加载 |
| 5 | 北向资金 NorthboundView | ✅ 日期选择 | 60s轮询 |
| 6 | 龙虎榜 DragonTigerView | ✅ 日期选择 | 120s轮询 |
| 7 | 行业对比 IndustryCompareView | ✅ 日期选择 | 120s轮询 |
| 8 | 限售解禁 LockupView | — | 300s轮询 |
| 9 | 资讯 NewsView | ✅ 日历导航 | 300s轮询 |
| 10 | 热点题材 HotReasonView | ✅ 日期选择 | 30s轮询 |
| 11 | 自选 WatchlistView | — | — |
| 12 | 投资组合 PortfolioView | — | — |
| 13 | AI对话 ChatView | — | — |
| 14 | 缠论 LayerDetailView | — | — |
| 15 | 登录 LoginView | — | — |

---

## 三、当前系统状态 （2026-06-11 18:00）

### Redis 数据 （18:06 快照）

| 数据 | 容量 | 日期 | TTL |
|:-----|:-----|:-----|:----|
| stock_basic | 5,542 只 | 6/11 | 24h |
| index_list | 5 指数 | 6/11 | 24h |
| northbound | 1 条 | 6/11 | 24h |
| northbound_minute | 262 点 | 6/11 | 24h |
| hot_reason | 78 条 | 6/11 | 24h |
| dragon_tiger | 512 条 | 6/11 | 24h |
| industry_compare | 99 行业 | 6/11 | 24h |
| industry_treemap | 99 行业 | 6/11 | 24h |
| analysis:top_gainers | 100 条 | 6/11 | 24h |
| fund_flow | 40 只×20日(不再刷新) | 6/11 | 12h (过期) |
| lockup_upcoming | 398 条 | 6/11~9/9 | 7天 |
| global_news / cls_news | 各 100 条 | 6/11 实时 | 24h |
| kline_day | 5,528 只×365天 | 6/10（结算中→18:00自动更新） | 12h |
| kline_5min | 410 只 × 60 条 | 6/11 盘中 | 12h |
| kline_15min | 408 只 × 40 条 | 6/11 盘中 | 12h |
| kline_30min | 413 只 × 40 条 | 6/11 盘中 | 12h |
| kline_60min | 412 只 × 40 条 | 6/11 盘中 | 12h |
| rollover_done_today | ✅ 已设置 | 6/11 17:45 | 24h |

### MySQL 数据

| 表 | 行数 | 日期范围 | 交易日数 |
|:---|:-----|:---------|:--------|
| stock_daily | 331,402 | 1996-11-22 ~ 2026-06-11 | 4,272天 |
| index_daily | 10 | 6/10~6/11 | 2天 |
| industry_daily | 198 | 6/10~6/11 | 2天 |
| northbound_daily | 2 | 6/10~6/11 | 2天 |
| hot_reason_daily | 152 | 6/10~6/11 | 2天 |
| dragon_tiger_daily | 819 | 6/10~6/11 | 2天 |
| info_news | 344 | 6/10~6/11 | 2天 |

---

## 四、今日修复清单 （6月11日，共23项）

### 🔴 重大修复 （6项）

| # | 问题 | 根因 | 修复 |
|:-:|:-----|:-----|:------|
| 1 | K线数据缺失 | seed_kline 无CSV时只采5指数 | 新增Redis stock_basic兜底，25min全量采5528只 |
| 2 | MySQL stock_daily 仅10万行 | batch_kline_to_mysql 仅采指数 | 修复并行采集，331k行9s完成 |
| 3 | 历史库连接失败 | application.yml url→jdbc-url | 修复配置+HikariCP冲突 |
| 4 | PE/PB/市值全为0 | 降级脚本MySQL NULL→0覆盖 | 腾讯API重采，3800只有PE |
| 5 | 涨跌排行无数据 | 无采集器写入3个analysis key | stock_basic排序取30写入 |
| 6 | 分钟K线缺失(TTL=1h) | seed_kline TTL=3600s | 改43200s + run_collector自动刷新 |

### 🟡 功能改进 （9项）

| # | 改进 | 涉及文件 |
|:-:|:------|:---------|
| 1 | 北向资金分钟级 262点管道 | auto_seed + RedisDataController + NorthboundView |
| 2 | 资金流向字段名双兼容 | FundFlowView.vue |
| 3 | 锁解 floatRatio 正确展示 | LockupView.vue |
| 4 | 复盘模式 WebSocket 守卫 | HomeView.vue |
| 5 | onDateChange 补全3个 loader | HomeView.vue |
| 6 | ReviewDatePicker 提示文案 | 3种状态标签 |
| 7 | data_rollover() 重构 | 4段式 + 异常兜底 + 重入保护 |
| 8 | K线结算延迟自动重试 | run_collector.py |
| 9 | 清理废弃文件12项 | seed_signals / batch / HDFS脚本等 |

### 🟢 配置修复 （8项）

| # | 修复 | 文件 |
|:-:|:-----|:------|
| 1 | 后端TZ=Asia/Shanghai | docker-compose.yml |
| 2 | history datasource独立前缀 | application.yml |
| 3 | 分钟K线 TTL 1h→12h | seed_kline.py |
| 4 | seed_kline 300→500只 | seed_kline.py |
| 5 | 降级脚本完全移除 | — |
| 6 | rollover_done_today 标志 | auto_seed.py |
| 7 | agg_lockup.py 同步到容器 | — |
| 8 | 重复ffr/al调用移除 | auto_seed.py |

---

## 五、组件部署

| 组件 | 容器 | 端口 | 状态 |
|:-----|:-----|:-----|:----:|
| **Redis** | redis:7 | 6379 | ✅ 11,850+ key |
| **MySQL** | mysql:8 | 3306 | ✅ stock 主库 + history 历史库 |
| **Backend** | backend | 8082 | ✅ 17端点全部正常 |
| **Frontend** | frontend | 5173 | ✅ 14视图全部可用 |
| **Collector** | data-collector | — | ✅ PID 1: run_collector |
| **AI Service** | ai-service | 8000 | ✅ 缠论分析可用 |

---

## 六、系统状态评估

### ✅ 已验证正常（6项）

| # | 项目 | 验证结果 | 说明 |
|:-:|:-----|:---------|:------|
| 1 | StockDetailView 字段映射 | ✅ 正确 fallback | `info.changePct ?? info.changePercent ?? 0` 已正确映射，无实际影响 |
| 2 | 分钟K线覆盖（4周期） | ✅ 400+只/周期 | 5min 410只、15min 408只、30min 413只、60min 412只 + 5指数 |
| 3 | MySQL 信号表归档 | ✅ 6/11数据已归档 | 每日 snapshot 正常执行，7张表均有6/11数据 |
| 4 | 收盘快照 rollover | ✅ 已执行 | 17:45:51 完成，标志位已设置 |
| 5 | 新闻实时更新 | ✅ 每5分钟 | 17:48 日志确认新闻刷新正常 |

### ⏳ 时间积累中（3项）

| # | 问题 | 状态 | 预期解决 |
|:-:|:-----|:-----|:---------|
| 1 | 腾讯API结算数据未发布 | ⏳ K线最新=20260610 | 18:00~19:00 自动更新 |
| 2 | MySQL信号表历史天数不足 | ⏳ 仅2天(6/10~6/11) | 每日归档自动积累，1个月后≥22天 |
| 3 | 分钟K线后排股票未覆盖 | ⏳ 前500只覆盖 | run_collector循环逐步填充 |

### ❌ 已移除（上游API不可达）

| # | 功能 | 移除原因 |
|:-:|:-----|:---------|
| 1 | **资金流向页面** (FundFlowView) | 数据源 `push2.eastmoney.com` 被企业防火墙屏蔽，推导数据无意义 |
| 2 | **行业云图成分股** (SectorDetailPanel + enrich) | 数据源 `push.eastmoney.com` + akshare 被防火墙屏蔽 |
| 3 | **fund_flow_refresh.py** | 对应采集脚本已废弃 |
| 4 | **ffr.py** (容器入口) | 对应入口脚本已废弃 |
| 5 | `_enrich_treemap_with_children()` | 云图 enrich 函数已移除 |

---

## 七、系统核心数据流

```
交易日 09:00~15:00:
  run_collector 循环（每5min）
    ├─ 新闻采集（CSV + Redis） ← 唯一实时更新的数据
    ├─ 北向分时采集（262点）
    ├─ 分钟K线TTL检查 → 后台Popen
    ├─ 日K结算检查 → 后台Popen（若最新K线日期≠今日）
    └─ 前端标签: "⏳ 交易时段 · 展示上一个交易日数据"

交易日 15:00 触发:
  data_rollover()（每天一次）
    ├─ Step 1: fill_static() → 行情+信号+锁解
    ├─ Step 2: seed_analysis() → 涨跌排行
    ├─ Step 3: refresh_kline() + rebuild_index() → K线+指数
    └─ Step 4: daily_snapshot_to_mysql() → MySQL归档

非交易日:
  无操作，前端标签: "📅 非交易日 · 展示最近交易日数据"
```
