# 股票 API 文档

## GET /api/stock/list — 股票列表

分页查询股票列表，支持搜索和行业筛选。

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| page | int | 否 | 页码，默认 1 |
| size | int | 否 | 每页条数，默认 20 |
| keyword | string | 否 | 搜索关键字（代码/名称） |
| industry | string | 否 | 行业筛选 |
| sortField | string | 否 | 排序字段 |
| sortOrder | string | 否 | asc / desc |

**响应示例:**
```json
{
  "records": [
    {
      "code": "000001",
      "name": "平安银行",
      "price": 11.45,
      "change_pct": 1.32,
      "change": 0.15,
      "volume": 125000000,
      "industry": "银行",
      "pe": 5.6
    }
  ],
  "total": 4500,
  "size": 20,
  "current": 1
}
```

---

## GET /api/stock/:code — 股票详情

**响应示例:**
```json
{
  "code": "000001",
  "name": "平安银行",
  "market": "SZ",
  "industry": "银行",
  "price": 11.45,
  "open": 11.30,
  "high": 11.52,
  "low": 11.28,
  "preClose": 11.30,
  "volume": 125000000,
  "amount": 1425000000,
  "changePercent": 1.32,
  "turnoverRate": 0.65,
  "pe": 5.6,
  "pb": 0.72,
  "totalMarketCap": 222150000000,
  "floatMarketCap": 222150000000
}
```

---

## GET /api/stock/kline/:code — 日K线数据

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| days | int | 否 | 最近N天，默认 365 |
| freq | string | 否 | 频率: daily/weekly/monthly |

**响应示例:**
```json
[
  {
    "tradeDate": "2026-05-08",
    "openPrice": 11.30,
    "highPrice": 11.52,
    "lowPrice": 11.28,
    "closePrice": 11.45,
    "volume": 125000000,
    "amount": 1425000000,
    "changePercent": 1.32
  }
]
```

---

## GET /api/stock/search — 股票搜索

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| keyword | string | 是 | 搜索关键字 |
| size | int | 否 | 返回条数，默认 10 |

---

## GET /api/stock/industries — 行业列表

获取所有行业分类。
