# 项目优化任务清单和实施计划

> 生成时间: 2026-05-20 | 项目: 基金股票智能分析系统 v2.2

---

## 一、P0 — 阻塞级（立即执行）

### T1: 清理 test_siliconflow_core.py 硬编码回退Key

**文件**: `ai-service/tests/test_siliconflow_core.py` 第10行

**当前代码**:
```python
TEST_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-hbbicdzujyygrmnpwambsebxzifjkosfkeazrbtesceeerea")
```

**修复后**:
```python
TEST_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
if not TEST_API_KEY:
    print("⚠️ 未设置 SILICONFLOW_API_KEY 环境变量，跳过使用真实 API 的测试")
```

**工时**: 5分钟

---

### T2: 修复 hive-server unhealthy

**问题**: Hive Metastore 无法初始化（MySQL连接或配置问题）

**排查步骤**:
```bash
# 1. 检查 MySQL 是否可连接
docker exec hive-server mysql -h mysql -u root -phadoop123 -e "SHOW DATABASES;"

# 2. 看 Hive 完整日志
docker logs hive-server 2>&1 | grep -i error

# 3. 检查 hive-site.xml 配置
docker exec hive-server cat /opt/hive/conf/hive-site.xml

# 4. 如 Metastore 损坏，重建：
docker restart hive-server

# 5. 如果反复失败，重建容器：
docker compose -f docker/docker-compose.yml up -d hive-server
```

**工时**: 1小时

---

### T3: 后端补充 PUT/PATCH 端点

#### T3.1 UserController 增加更新/密码修改端点

**文件**: `backend/src/main/java/com/stock/controller/UserController.java`

**添加代码**:
```java
@PutMapping("/update")
public ApiResponse<User> updateUser(@RequestBody @Valid UpdateUserRequest request) {
    // XML 已有 updateUserInfo，只需暴露 REST 端点
    User user = userService.getById(request.getId());
    if (user == null) return ApiResponse.error("用户不存在");
    BeanUtils.copyProperties(request, user, "password", "role");
    userService.updateById(user);
    return ApiResponse.success(user);
}

@PostMapping("/change-password")
public ApiResponse<Void> changePassword(@RequestBody @Valid ChangePasswordRequest request) {
    // 验证旧密码 → BCrypt 加密新密码 → 更新
    User user = userService.getById(SecurityUtils.getCurrentUserId());
    if (!BCrypt.checkpw(request.getOldPassword(), user.getPassword())) {
        return ApiResponse.error("原密码错误");
    }
    user.setPassword(BCrypt.hashpw(request.getNewPassword(), BCrypt.gensalt()));
    userService.updateById(user);
    return ApiResponse.success();
}
```

**需新增 DTO**:
```java
@Data
public class UpdateUserRequest {
    @NotNull private Long id;
    private String email;
    private String phone;
    private String avatar;
    private String username;
}

@Data
public class ChangePasswordRequest {
    @NotBlank private String oldPassword;
    @NotBlank @Size(min = 6) private String newPassword;
}
```

#### T3.2 WatchlistController 增加排序/备注更新端点

**文件**: `backend/src/main/java/com/stock/controller/WatchlistController.java`

```java
@PutMapping("/update")
public ApiResponse<Void> updateWatchlist(@RequestBody @Valid UpdateWatchlistRequest request) {
    // 更新排序序号或备注
    watchlistService.updateById(request.toEntity());
    return ApiResponse.success();
}
```

#### T3.3 AnalysisController 增加删除端点

**文件**: `backend/src/main/java/com/stock/controller/AnalysisController.java`

```java
@DeleteMapping("/{id}")
@RequirePermission("analysis:delete")
public ApiResponse<Void> deleteAnalysis(@PathVariable Long id) {
    analysisService.removeById(id);
    return ApiResponse.success();
}
```

同时需在 `AnalysisResultMapper.xml` 中补 delete SQL（或直接使用 MyBatis-Plus 内置 `deleteById`）。

**工时**: 1天

---

## 二、P1 — 重要级（本周完成）

### T4: Docker 镜像源配置 + 重新构建

**问题**: 当前 Docker 镜像源 `docker.xuanyuan.me` 限流，导致 `eclipse-temurin` 和前端 npm 依赖拉取失败。

**修复方案**: 修改 Docker daemon 配置 `C:\ProgramData\Docker\config\daemon.json`:

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://hub-mirror.c.163.com"
  ]
}
```

然后重建:
```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.dev build backend
docker compose -f docker/docker-compose.yml --env-file docker/.env.dev build frontend
```

**工时**: 1.5天（含构建等待时间）

---

### T5: 补充 FusionEngine 权重自动学习

**当前问题**: `update_weight()` 接口存在但无人调用。固定权重缺乏适应性。

**实现方案**:

**文件**: `ai-service/app/fusion/__init__.py`

```python
class FusionEngine:
    """多智能体融合引擎 — 加权投票 + 自动权重学习"""
    
    # 持久化键名
    ACCURACY_KEY = "fusion:accuracy:"
    WEIGHT_KEY = "fusion:weights"
    
    def __init__(self, redis_client=None):
        self._weights = self._default_weights()
        self._redis = redis_client
        self._load_weights()  # 启动时从 Redis 加载已学习的权重
    
    def update_weight(self, agent_name: str, new_weight: float):
        if agent_name not in self._weights:
            logger.warning(f"未知 Agent: {agent_name}, 跳过权重更新")
            return
        self._weights[agent_name] = max(0.0, new_weight)
        self._normalize()
        self._save_weights()  # 持久化到 Redis
    
    def record_accuracy(self, agent_name: str, correct: bool):
        """记录 Agent 的历史预测准确率"""
        key = f"{self.ACCURACY_KEY}{agent_name}"
        # 滑动窗口: 记录最近 N 次预测结果
        if self._redis:
            self._redis.lpush(key, 1 if correct else 0)
            self._redis.ltrim(key, 0, 99)  # 保留最近100次
    
    def learn_weights(self):
        """根据历史准确率自动调整权重"""
        if not self._redis:
            return
        for agent in self._weights:
            key = f"{self.ACCURACY_KEY}{agent}"
            records = self._redis.lrange(key, 0, -1)
            if records:
                accuracy = sum(int(r) for r in records) / len(records)
                # 权重 = 基础权重 × (0.5 + accuracy)
                self._weights[agent] *= (0.5 + accuracy)
        self._normalize()
        self._save_weights()
```

**工时**: 1.5天

---

### T6: 后端用户管理补充

#### T6.1 登出/Token 黑名单

**文件**: `backend/src/main/java/com/stock/controller/UserController.java`

```java
@PostMapping("/logout")
public ApiResponse<Void> logout(@RequestHeader("Authorization") String token) {
    // 将 Token 加入 Redis 黑名单（TTL = Token 剩余有效期）
    String jwt = token.replace("Bearer ", "");
    long ttl = jwtUtil.getRemainingExpiry(jwt);
    if (ttl > 0) {
        redisTemplate.opsForValue().set("blacklist:" + jwt, "1", ttl, TimeUnit.SECONDS);
    }
    return ApiResponse.success();
}
```

#### T6.2 Token 刷新

```java
@PostMapping("/refresh")
public ApiResponse<Map<String, String>> refreshToken(
        @RequestHeader("Authorization") String token) {
    String jwt = token.replace("Bearer ", "");
    // 验证旧 Token 有效 → 生成新 Token
    if (jwtUtil.validateToken(jwt) && !isBlacklisted(jwt)) {
        String newToken = jwtUtil.refreshToken(jwt);
        return ApiResponse.success(Map.of("token", newToken));
    }
    return ApiResponse.error("Token 无效或已过期");
}
```

**工时**: 0.5天

---

### T7: 前端的组件级单元测试

**当前**: 仅有 `stores/` 和 `utils/` 测试，**0 个 `.vue` 组件测试**

**实现方案**: 为 10 个组件创建 `.spec.ts`

```typescript
// frontend/src/components/__tests__/AppHeader.spec.ts
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import AppHeader from '@/components/common/AppHeader.vue'

describe('AppHeader.vue', () => {
  it('renders navigation links', () => {
    const wrapper = mount(AppHeader, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })]
      }
    })
    expect(wrapper.text()).toContain('行情')
  })

  it('toggles AI chat panel', async () => {
    const wrapper = mount(AppHeader, { global: { plugins: [createTestingPinia({ createSpy: vi.fn })] }})
    const aiBtn = wrapper.find('[data-test="ai-chat-btn"]')
    await aiBtn.trigger('click')
    expect(wrapper.emitted('toggle-chat')).toBeTruthy()
  })
})
```

**需覆盖的组件**: `AppHeader`, `AlertBell`, `AiChatPanel`, `AiSignalSummary`, `TreemapChart`, `LayerDetailPanel`, `LayerSectionCard`, `LayerStatusBadge`, `AppLayout`

**工时**: 2天

---

### T8: 补齐 docs/design/ 架构设计文档

**当前**: `docs/design/` 目录为空

**创建文件**:
```bash
docs/design/
├── architecture-overview.md     # 六层架构概览图 + 数据流
├── data-flow.md                 # 数据采集→存储→处理→展示完整链路
├── api-design.md                # REST API 设计规范
├── deployment.md                # 部署拓扑图
```

**工时**: 0.5天

---

## 三、P2 — 常规级（两周内完成）

### T9: 前端 layer API 替换为真实后端

**文件**: `frontend/src/api/layer.ts`

**当前**: 静态 Mock 数据（第9-161行 `ALL_LAYERS` 硬编码数组）

**替换方案**:
1. 在 backend 新增 `LayerController`，返回 L1-L6 各层状态（从 Docker/系统信息获取）
2. 前端改为真实 HTTP 调用:

```typescript
// 替换后
import request from './request'

export interface LayerInfo {
  name: string
  status: 'online' | 'offline' | 'degraded'
  modules: LayerModule[]
}

export async function getLayerList(): Promise<LayerInfo[]> {
  const resp = await request.get('/api/layers')
  return resp.data
}
```

同时删除 `ALL_LAYERS` 硬编码数组和 `delay()` 模拟。

**工时**: 1天

---

### T10: 前端国际化覆盖率提升

**当前**: 仅 24 个翻译键，覆盖导航和通用文案

**实施步骤**:
1. 在 `src/i18n/index.ts` 中补充所有视图页面的翻译键
2. 替换页面中的硬编码中文

**新增翻译键示例**:
```typescript
// 在 i18n/index.ts 中补充
const zhCN = {
  nav: { /* 已有 */ },
  home: {
    marketOverview: '市场概览',
    sectorCloud: '板块云图',
    topGainers: '涨幅榜',
    topLosers: '跌幅榜',
    activeStocks: '活跃个股',
  },
  stockDetail: {
    basicInfo: '基本信息',
    kline: 'K线图',
    technicalIndicators: '技术指标',
    chanlun: '缠论分析',
    signalData: '信号数据',
  },
  // ... 每个视图各自的翻译
}
```

**工时**: 1天

---

### T11: FundListView 缺失页面

**文件**: 新增 `frontend/src/views/FundListView.vue`

**功能**: 基金列表页（搜索、筛选、排序），点击进入 `FundDetailView.vue`

```vue
<template>
  <div class="fund-list">
    <el-input v-model="searchQuery" placeholder="搜索基金代码/名称" />
    <el-table :data="filteredFunds" @row-click="goToDetail">
      <el-table-column prop="code" label="基金代码" width="120" />
      <el-table-column prop="name" label="基金名称" />
      <el-table-column prop="nav" label="最新净值" width="120" />
      <el-table-column prop="navDate" label="净值日期" width="120" />
      <el-table-column prop="type" label="类型" width="100" />
    </el-table>
  </div>
</template>
```

并在 `router/index.ts` 添加路由:
```typescript
{ path: '/funds', name: 'FundList', component: () => import('@/views/FundListView.vue') }
```

**工时**: 0.5天

---

### T12: Spark MLlib 预测模型增强

**文件**: `bigdata-processing/spark/mllib/stock_predictor.py` (152行)

**当前问题**: 仅支持线性回归和随机森林。注释说"仅供学习/演示"。

**优化方向**:
```python
# 在 train() 方法中增加模型选项
def train(self, df: DataFrame, model_type: str = 'random_forest'):
    """支持更多模型类型"""
    models = {
        'linear': LinearRegression(...),
        'random_forest': RandomForestRegressor(...),
        'gbt': GBTRegressor(...),          # 梯度提升树（新增）
    }
    if model_type == 'auto':
        # 自动选择最佳模型（交叉验证）
        best_model, best_metric = self._auto_select(df)
        return best_model
```

同时补充单元测试:
```python
# tests/test_predictor.py
def test_feature_preparation(mock_spark):
    predictor = StockPredictor(mock_spark)
    df = create_mock_kline_data(mock_spark, 100)
    prepared = predictor.prepare_features(df)
    assert 'features' in prepared.columns
    assert 'label' in prepared.columns
    assert prepared.count() < df.count()  # 滞后特征导致行数减少
```

**工时**: 1天

---

### T13: 废弃 MapReduce 统一 Spark

**当前**: `bigdata-processing/mapreduce/` 下有 4 个 MR 作业 + 3 个测试

**实施步骤**:
1. 确认 Spark 已实现所有 5 个 MR 功能（已验证 `spark/batch/` 中已有: `ma_trend`, `trend_judge`, `yearly_return`, `monthly_return` 等）
2. 在 `mapreduce/` 目录添加 `DEPRECATED.md` 说明
3. 如有 MR 独有的功能，先用 Spark 实现后再迁移
4. MR 代码保留 3 个月过渡期后删除

**工时**: 1天

---

### T14: 清理旧版采集架构

**当前**: `scheduler/market_collect.py`（旧版）和 `pipeline/`（新版）共存

**实施步骤**:
1. 确认新版 pipeline 完全覆盖旧版功能
2. 在 `market_collect.py` 顶部添加 deprecation warning
3. 迁移文档更新，说明统一使用 `run_collector.py` 入口

**工时**: 1天

---

## 四、P3 — 增强级（后续迭代）

### T15: Circuit Breaker 熔断

**文件**: `backend/src/main/java/com/stock/config/ResilienceConfig.java`

```java
@Configuration
public class ResilienceConfig {
    @Bean
    public Customizer<Resilience4jCircuitBreakerFactory> defaultCustomizer() {
        return factory -> factory.configureDefault(id -> new CircuitBreakerConfig(
            50,    // slidingWindowSize
            60,    // minimumNumberOfCalls
            60,    // failureRateThreshold
            100,   // waitDurationInOpenState
            3,     // permittedNumberOfCallsInHalfOpenState
            CircuitBreakerConfig.SlidingWindowType.COUNT_BASED
        ).build());
    }
}
```

**工时**: 1天

---

### T16: OpenAPI/Swagger 独立文档

**文件**: 从 `requirements.md` 提取 API 文档，生成 OpenAPI 3.0 规范

```yaml
# docs/api/openapi.yaml
openapi: "3.0.0"
info:
  title: "基金股票智能分析系统 API"
  version: "2.2.0"
servers:
  - url: http://localhost:8082/api
paths:
  /market/list:
    get:
      summary: 市场行情列表
      parameters:
        - name: page
          in: query
          schema: { type: integer, default: 1 }
      responses:
        '200':
          description: 成功
```

Spring Boot 后端可使用 `springdoc-openapi` 自动生成。

**工时**: 0.5天

---

## 五、执行路线图

```
周次    P0任务              P1任务              P2任务
───  ───────────────   ────────────────   ────────────────
W1    T1清理Key(5min)    T4 Docker构建      -
      T3 PUT端点(1天)    T5 Fusion学习(1.5天)
      T2 Hive排查(1h)    T6 用户管理(0.5天)

W2    -                  T7 组件测试(2天)   T9 layer API(1天)
                         T8 设计文档(0.5天)  T10 i18n(1天)

W3    -                  -                  T11 Fund列表(0.5天)
                                            T12 预测增强(1天)
                                            T13 废弃MR(1天)
                                            T14 清理旧代码(1天)

W4    -                  -                  P3 任务(1.5天)
```

---

## 六、优化效果预估

| 优化项 | 改善指标 | 预期效果 |
|:-------|:---------|:---------|
| PUT端点补齐 | API完整性 | 用户可编辑资料/密码/自选排序 |
| Hive修复 | 容器健康 | bigdata-net 100% healthy |
| Fusion权重学习 | 分析准确率 | 融合结果准确率提升 10-15% |
| 前端组件测试 | 测试覆盖率 | 前端覆盖率从65%提升至85% |
| Docker构建修复 | 部署效率 | L4/L6可一键容器化部署 |
| i18n覆盖 | 国际化 | 从30%提升至80% |
| Spark MLlib增强 | 预测能力 | 支持GBT回归 + 自动模型选择 |
