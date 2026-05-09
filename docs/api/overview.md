# API 接口文档

> 基于 Spring Boot + MyBatis Plus 构建的 RESTful API

## 基础信息

| 项目 | 值 |
|:-----|:----|
| 基础路径 | `http://localhost:8080/api` |
| 数据格式 | `application/json` |
| 认证方式 | Bearer Token (JWT) |
| 字符集 | UTF-8 |

## 接口总览

| 模块 | 路径前缀 | 主要接口 | 文档 |
|:-----|:---------|:---------|:----:|
| **股票** | `/api/stock` | 列表/详情/K线 | [stock-api.md](./stock-api.md) |
| **分析** | `/api/analysis` | 收益率/趋势/筛选/行业 | [analysis-api.md](./analysis-api.md) |
| **基金** | `/api/fund` | 列表/详情/净值/持仓 | [fund-api.md](./fund-api.md) |
| **用户** | `/api/user` | 登录/注册/信息 | - |
| **自选** | `/api/watchlist` | 增删改查 | - |

## 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

分页响应:
```json
{
  "records": [...],
  "total": 100,
  "size": 20,
  "current": 1,
  "pages": 5
}
```

## 错误码

| 状态码 | 说明 |
|:------:|:-----|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |
