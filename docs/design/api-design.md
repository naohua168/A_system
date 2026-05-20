# REST API 设计规范

> 版本: v2.2 | 后端端口: 8082 | AI 服务端口: 8000

## 基础规范

- **统一响应格式**: `{ code, message, data, timestamp }`
- **分页格式**: `{ records, total, page, size, totalPages }`
- **认证方式**: `Authorization: Bearer <JWT Token>`
- **内容类型**: `application/json`

## 端点清单

### 后端 API (`/api/`)

| 组 | 前缀 | 端点数 | 主要功能 |
|:---|:-----|:------:|:---------|
| Market | `/api/market` | 10 | 行情列表/详情/K线/搜索/行业 |
| Analysis | `/api/analysis` | 9 | 收益率/趋势/筛选/缠论/相关/排行, +DELETE |
| Fund | `/api/fund` | 4 | 基金信息/净值/持仓/排行 |
| Signal | `/api/signal` | 14 | 热点/北向/龙虎榜/资金流/解禁/概念 |
| Info | `/api/info` | 9 | 研报/一致预期/公告/新闻/快讯 |
| Index | `/api/index` | 4 | 指数行情/成分/日K |
| User | `/api/user` | 7 | 登录/注册/信息/更新/改密码/登出/刷新 |
| Watchlist | `/api/watchlist` | 4 | 列表/添加/删除/更新 |
| **合计** | | **61+** | |

### AI 服务 (`/api/ai/`)

| 端点 | 方法 | 功能 |
|:-----|:----:|:-----|
| `/api/ai/chat` | POST | 对话 (注入实时行情) |
| `/api/ai/chat/stream` | POST | SSE 流式对话 |
| `/api/ai/analyze` | POST | 多智能体深度分析 |
| `/api/ai/debate` | POST | 看涨/看跌辩论 |
| `/api/ai/fuse` | POST | 融合分析 |
| `/api/ai/memory/{code}` | GET | 历史记忆查询 |
| `/api/ai/models` | GET | 模型列表 |
| `/api/ai/status` | GET | 服务状态 |
| `/health` | GET | 健康检查 |
