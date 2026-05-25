# 数据层 vs 前端展示层 — 逐页对比分析

## 总体数据

```
数据层: 133,408 行 / 13 张表有数据 / 4 张表为空
前端页面: 20+ 视图 / 50+ API 端点
```

---

## 一、首页 HomeView — 六大模块逐项检查

### 1.1 大盘指数轮播卡

| 维度 | 数据层 | 前端需求 | 判定 |
|:-----|:-------|:---------|:----:|
| 表 | `market_index` (11行) | 4个指数(上证/深证/创业板/科创) | ✅ |
| 字段 | `index_code, index_name` | `indexCode, indexName` | ✅ |
| 价格 | `index_daily.close_point` (2011行) | `price=closePoint` | ✅ **有2年历史** |
| 涨跌幅 | `index_daily.change_percent` | `changePercent` | ✅ |

### 1.2 信号层快捷卡片（4张）

| 卡片 | API 端点 | 数据表 | 数据量 | 判定 |
|:-----|:---------|:-------|:------|:----:|
| 🔥 题材热点 | `/signal/hot-reason` | `signal_hot_reason` | 248行/3日 | ✅ |
| 🌐 北向资金 | `/signal/northbound/latest` | `signal_northbound` | 262行 | ✅ |
| 📊 行业排行 | `/signal/industry-compare` | `signal_daily_industry` | 240行/1日 | ✅ |
| 🐉 龙虎榜 | `/signal/dragon-tiger/daily` | `signal_dragon_tiger_detail` | 86行/1日 | ✅ |

### 1.3 板块涨跌云图

| 维度 | 数据层 | 前端需求 | 判定 |
|:-----|:-------|:---------|:----:|
| API | N/A | `/api/analysis/sector-ranking` | ❌ |
| 数据表 | `analysis_result = 0行` | `industry, stockCount, avgChangePct` | ❌ **空表 -> 板块云图空白** |

### 1.4 热门股票网格

| 维度 | 数据层 | 前端需求 | 判定 |
|:-----|:-------|:---------|:----:|
| API | `/api/market/list` | 12只热门股 | ✅ |
| 数据表 | `stock` (5,544行) | `stockCode,stockName,price,changePct` | ✅ |

---

## 二、行情页 — 逐项

### 2.1 股票列表 StockListView

| 需求 | 数据层 | 判定 |
|:-----|:-------|:----:|
| 分页列表 | `stock` 5,544行 | ✅ |
| 行业筛选 | `stock.industry` 列 | ✅ |
| 搜索 | `stock.stock_code/stock_name` | ✅ |

### 2.2 个股详情 StockDetailView

| 模块 | API | 数据表 | 数据 | 判定 |
|:-----|:----|:-------|:----|:----:|
| 基本信息 | `/market/{code}` | `stock` | 5,544 | ✅ |
| K线图 | `/market/kline/{code}` | `stock_daily` | **124k行/589只/2年** | ✅ |
| 概念板块 | `/signal/concept-blocks/{code}` | `signal_concept_block` | **28行/7只** | ⚠️ 仅7只有数据 |
| 资金流向 | `/signal/fund-flow/{code}` | `signal_fund_flow` | **30行/3只** | ⚠️ 仅3只有数据 |
| 解禁日历 | `/signal/lockup/stock/{code}` | `signal_lockup_detail` | 55行/6只 | ✅ |
| 技术分析 | `/analysis/{code}` | `analysis_result` | **0行** | ❌ 全部空白 |

---

## 三、信号页 — 逐项

| 页面 | API | 数据表 | 数据量 | 判定 |
|:-----|:----|:-------|:------|:----:|
| HotReasonView | `/signal/hot-reason` | `signal_hot_reason` | 248行 | ✅ |
| DragonTigerView | `/signal/dragon-tiger/daily` | `signal_dragon_tiger_detail` | 86行 | ✅ |
| NorthboundView | `/signal/northbound/latest` | `signal_northbound` | 262行 | ✅ |
| IndustryCompareView | `/signal/industry-compare` | `signal_daily_industry` | 240行 | ✅ |
| LockupView | `/signal/lockup/upcoming` | `signal_lockup_detail` | 55行 | ✅ |
| FundFlow | `/signal/fund-flow/{code}` | `signal_fund_flow` | 30行/3只 | ⚠️ 覆盖少 |
| ConceptBlock | `/signal/concept-blocks/{code}` | `signal_concept_block` | 28行/7只 | ⚠️ 覆盖少 |

---

## 四、基金页

| 页面 | API | 数据表 | 数据量 | 判定 |
|:-----|:----|:-------|:------|:----:|
| FundListView | `/fund/list` | `fund` | **0行** | ❌ 全部空白 |
| FundDetailView | `/fund/{code}` | `fund` | **0行** | ❌ |
| FundNav | `/fund/{code}/nav` | `fund_nav` | **0行** | ❌ |
| FundHolding | `/fund/{code}/holdings` | `fund_holding` | **0行** | ❌ |

---

## 五、总结：问题清单

| 优先级 | 问题 | 影响 | 涉及表 |
|:------:|:-----|:-----|:------|
| **P0** | `analysis_result` 为空 | 首页板块云图空白 + 个股分析空白 | `analysis_result` |
| **P1** | `fund/fund_nav/fund_holding` 为空 | 基金页面全空白 | `fund` 系列 |
| **P2** | `signal_concept_block` 覆盖少 | 个股详情概念板块空白 | `signal_concept_block` |
| **P2** | `signal_fund_flow` 覆盖少 | 个股详情资金流向空白 | `signal_fund_flow` |
| ✅ | K线/指数/热点/北向/行业/龙虎榜/解禁 | 全部正常 | 7张表就绪 |
