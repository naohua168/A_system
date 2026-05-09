# 基金 API 文档

## GET /api/fund/list — 基金列表

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| page | int | 否 | 页码 |
| size | int | 否 | 每页条数 |
| type | string | 否 | 基金类型筛选 |

---

## GET /api/fund/:code — 基金详情

**响应示例:**
```json
{
  "code": "000001",
  "name": "易方达蓝筹精选混合",
  "type": "混合型",
  "company": "易方达基金管理有限公司",
  "manager": "张坤",
  "establishDate": "2018-09-05",
  "scale": "528.65亿元",
  "nav": 1.6850,
  "accumulatedNav": 2.1350
}
```

---

## GET /api/fund/:code/nav — 基金净值

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|:-----|:----|:----:|:-----|
| days | int | 否 | 最近N天，默认 365 |

**响应示例:**
```json
[
  { "navDate": "2026-05-08", "nav": 1.6850, "accumulatedNav": 2.1350, "dailyReturn": 0.0125 }
]
```

---

## GET /api/fund/:code/holdings — 基金持仓

**响应示例:**
```json
[
  { "stockCode": "600519", "stockName": "贵州茅台", "ratio": 9.85 },
  { "stockCode": "00700", "stockName": "腾讯控股", "ratio": 8.52 }
]
```
