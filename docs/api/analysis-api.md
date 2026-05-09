# 分析服务 API 文档

## GET /api/analysis/:stockCode/yearly-return — 年收益率

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| years | int | 否 | 最近N年，默认 3 |

**响应示例:**
```json
[
  { "year": 2024, "yearlyReturn": 12.35, "startPrice": 10.20, "endPrice": 11.46 },
  { "year": 2025, "yearlyReturn": -3.58, "startPrice": 11.46, "endPrice": 11.05 },
  { "year": 2026, "yearlyReturn": 5.20, "startPrice": 11.05, "endPrice": 11.62 }
]
```

---

## GET /api/analysis/:stockCode/monthly-return — 月收益率

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| months | int | 否 | 最近N月，默认 12 |

---

## GET /api/analysis/:stockCode/trend — 趋势分析

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| days | int | 否 | 计算天数，默认 30 |

**响应示例:**
```json
{
  "stockCode": "000001",
  "trend": "震荡趋势",
  "currentPrice": 11.45,
  "ma5": 11.38,
  "ma10": 11.32,
  "ma20": 11.25,
  "changePct": 2.15
}
```

趋势类型: `上升趋势` / `下跌趋势` / `震荡趋势`

---

## POST /api/analysis/filter — 多条件筛选

**请求体:**
```json
{
  "industry": "银行",
  "minPrice": 10,
  "maxPrice": 50,
  "minChange": 1.0,
  "limit": 20
}
```

**响应:**
```json
[
  { "stockCode": "000001", "stockName": "平安银行", "price": 11.45, "changePct": 1.32 }
]
```

---

## GET /api/analysis/correlation — 相关性分析

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| codeA | string | 是 | 股票A |
| codeB | string | 是 | 股票B |
| days | int | 否 | 计算天数，默认 60 |

**响应:**
```json
{ "codeA": "000001", "codeB": "600519", "correlation": 0.3521 }
```

---

## GET /api/analysis/sector-ranking — 行业涨跌排行

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| tradeDate | string | 否 | 交易日，默认当天 |

**响应:**
```json
[
  { "industry": "白酒", "stockCount": 35, "avgChangePct": 2.15, "upCount": 28, "upRatio": 80.0 }
]
```
