# 数据层 vs 前端展示层 — 最终对比分析

> 生成时间: 2026-05-25 17:07

## 总体数据

```
17 张表: 14 张有数据 (133,608 行), 3 张为空 (fund 系列)
```

---

## 逐页对比

### 一、首页 HomeView

| 模块 | API | 数据表 | 数据量 | 判定 |
|:-----|:-----|:-------|:------:|:----:|
| 大盘指数卡片 | `/api/index/list` | `market_index`(11) + `index_daily`(2,011) | 4指数2年K线 | ✅ |
| 题材热点卡 | `/api/signal/hot-reason` | `signal_hot_reason` | 248行/3日 | ✅ |
| 北向资金卡 | `/api/signal/northbound/latest` | `signal_northbound` | 262行 | ✅ |
| 行业排行卡 | `/api/signal/industry-compare` | `signal_daily_industry` | 240行 | ✅ |
| 龙虎榜卡 | `/api/signal/dragon-tiger/daily` | `signal_dragon_tiger_detail` | 86行 | ✅ |
| **板块云图** | `/api/analysis/sector-ranking` | `analysis_result` | **201行** → **已修复** ✅ |
| 热门股票网格 | `/api/market/list` | `stock` | 5,544行 | ✅ |

### 二、行情页

| 页面 | 依赖表 | 数据量 | 判定 |
|:-----|:-------|:------:|:----:|
| StockListView | `stock` | 5,544行 | ✅ |
| StockDetailView-基本信息 | `stock` | 5,544 | ✅ |
| StockDetailView-K线图 | `stock_daily` | 124k行/589只(334只≥60天) | ✅ **超过前端60天默认** |
| StockDetailView-技术分析 | `analysis_result` | **201只** → **已修复** ✅ |
| StockDetailView-概念板块 | `signal_concept_block` | **28行/7只** | ⚠️ 大部分股票无数据 |
| StockDetailView-资金流向 | `signal_fund_flow` | **30行/3只** | ⚠️ 大部分股票无数据 |
| StockDetailView-解禁日历 | `signal_lockup_detail` | 55行/6只 | ✅ |

### 三、信号层页面

| 页面 | 依赖表 | 数据量 | 判定 |
|:-----|:-------|:------:|:----:|
| HotReasonView | `signal_hot_reason` | 248行 | ✅ |
| DragonTigerView | `signal_dragon_tiger_detail` | 86行 | ✅ |
| NorthboundView | `signal_northbound` | 262行 | ✅ |
| IndustryCompareView | `signal_daily_industry` | 240行 | ✅ |
| LockupView | `signal_lockup_detail` | 55行 | ✅ |
| ConceptBlockDetail | `signal_concept_block` | 28行 | ⚠️ 覆盖少 |
| FundFlowDetail | `signal_fund_flow` | 30行 | ⚠️ 覆盖少 |

### 四、基金页面 ❌

| 页面 | 依赖表 | 数据量 | 判定 |
|:-----|:-------|:------:|:----:|
| FundListView | `fund` | **0行** | ❌ 空白 |
| FundDetailView | `fund` + `fund_nav` | **0行** | ❌ 空白 |
| FundNav | `fund_nav` | **0行** | ❌ 空白 |
| FundHolding | `fund_holding` | **0行** | ❌ 空白 |

### 五、资讯页面

| 页面 | 依赖表 | 数据量 | 判定 |
|:-----|:-------|:------:|:----:|
| ClsNewsView | `info_cls_news` | 60行 | ✅ |
| GlobalNewsView | `info_global_news` | 400行 | ✅ |

---

## 总结：3 个等级的状态

| 等级 | 页面 | 数据 | 影响 |
|:----:|:-----|:----:|:-----|
| 🟢 **可用** | 首页 + 行情 + 信号 + 资讯 = **~15 个页面** | 全部就绪 | 核心功能正常 |
| 🟡 **部分可用** | 个股详情概念/资金流 | 仅覆盖 3~7 只股票 | 大部分股票空白 |
| 🔴 **不可用** | 基金列表/详情/净值/持仓 = **4 个页面** | 0 行 | 全部空白 |

## 前端可用性评分

| 维度 | 评分 | 说明 |
|:-----|:----:|:------|
| 首页仪表盘 | 95% | ✅ 全部6大模块有数据 |
| 行情浏览 | 90% | ✅ 列表+搜索+筛选+K线正常 |
| 个股详情 | 70% | ✅ K线/分析正常 ⚠️ 概念/资金流部分空白 |
| 信号分析 | 85% | ✅ 7个信号页面基本正常 |
| **基金理财** | **0%** | ❌ 4个基金页面全空白 |
| 资讯中心 | 100% | ✅ 财联社+全球资讯正常 |
