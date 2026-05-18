# 项目目录结构说明文档

> 更新时间: 2026-05-18
> 项目名称: 基金股票智能分析系统 (A_system)

---

## 一、项目全景图

```
A_system/
├── ai-service/                          # L5 - AI 智能服务层
├── analysis-algorithms/                 # L3 - 算法分析层
├── backend/                             # L4 - 后端 API 服务层
├── bigdata-processing/                  # L2 - 大数据处理层
├── data-collector/                      # L1 - 数据采集层
├── data/                                # 数据持久化目录 (Docker Volume)
├── docker/                              # Docker 容器化部署配置
├── docs/                                # 项目文档
├── frontend/                            # L6 - 前端展示层
├── logs/                                # 运行日志目录
├── scripts/                             # 实用工具脚本
├── LICENSE                              # MIT 开源许可证
└── README.md                            # 项目总览说明
```

---

## 二、各模块详细介绍

### 2.1 `data-collector/` — 数据采集层 (Python) — ✅ 已完工

```
data-collector/
├── __init__.py                          # 模块初始化
├── config.py                            # 全局配置（数据源参数、采集间隔、输出路径等）
├── pytest.ini                           # Pytest 测试配置
├── requirements.txt                     # Python 依赖包列表
├── final_demo.py                        # 端到端 Demo 入口
├── docker_collect.py                    # Docker 容器内全量采集（K线 + 资讯层）
├── _deploy_prod.py                      # 生产部署辅助脚本
│
├── collectors/                          # ★ 核心：多数据源采集器（10 个文件）
│   ├── __init__.py
│   ├── base_collector.py                # 采集器基类（定义采集接口、CSV 写入、重试机制）
│   ├── tencent_collector.py             # 腾讯财经 → 实时行情 / PE / PB / 市值 (HTTP, 优先级9)
│   ├── ths_hot_collector.py             # 同花顺 → 强势股题材归因 (HTTP, 优先级8)
│   ├── baidu_collector.py               # 百度股市通 → 概念板块 / 资金流向 (HTTP, 优先级7)
│   ├── mootdx_collector.py              # 通达信 TCP → K 线 / 五档盘口 / 逐笔 / F10 (TCP, 优先级10)
│   ├── akshare_extended_collector.py    # AKShare → 龙虎榜 / 解禁 / 行业 / 研报 (HTTP, 优先级6)
│   ├── akshare_extended_collector.py    # AKShare 扩展（冗余采集）(HTTP, 优先级5)
│   ├── kline_collector.py               # ★ 多周期 K 线采集器（8 种周期：1min~月K）
│   ├── stock_list.py                    # ★ 全市场股票代码源（腾讯扫描 + 缓存）
│   └── data_source_factory.py           # ★ 工厂模式 + 故障转移：按优先级依次尝试各数据源
│
├── adapters/                            # ★ 适配器层（全新重构）
│   ├── __init__.py
│   ├── base_adapter.py                  # 适配器基类/协议（AdaperMetadata, AdapterRegistry）
│   └── collector_adapters.py            # ★ 具体适配器实现（包装 Collector → 统一 DataFrame）
│
├── pipeline/                            # ★ 管道层（全新重构）
│   ├── __init__.py
│   ├── collection_pipeline.py           #   采集管道（fetch → validate → store 流水线）
│   ├── data_catalog.py                  # ★ 数据目录注册中心（16 种数据类型元信息）
│   └── orchestrator.py                  # ★ 并行采集编排器（分组并行 ThreadPoolExecutor）
│
├── storage/                             # ★ 统一存储管理层（全新重构）
│   ├── __init__.py
│   └── storage_manager.py               # ★ 统一存储管理器（CSV + MySQL + HDFS Facade）
│
├── crawler/                             # 爬虫模块
│   ├── __init__.py
│   ├── stock_crawler.py                 # 股票基础信息爬虫（个股列表、行业分类等）
│   └── fund_crawler.py                  # 基金信息爬虫（基金列表、净值、持仓等）
│
├── data/                                # 采集原始数据输出目录（CSV / JSON）
│
├── scheduler/                           # 调度器（保留原始调度机制）
│   ├── __init__.py
│   ├── market_collect.py                # 主调度入口：按模式（全量/增量/独立）执行采集
│   └── run_collector.py                 # 单次采集执行器（调用工厂采集并返回 DataFrame）
│
├── sql/                                 # ★ SQL DDL 定义（新增强化信息层）
│   ├── kline_ddl.sql                    #   K 线数据表 DDL（多周期适配）
│   ├── info_layer_ddl.sql               #   资讯层表 DDL（新闻/研报/一致预期/公告）
│   └── signal_layer_ext_ddl.sql         #   信号层扩展表 DDL
│
├── tests/                               # 单元测试
│   ├── __init__.py
│   ├── conftest.py                      # 测试夹具配置
│   ├── test_base_collector.py           # 基类采集器测试
│   └── test_collectors.py               # 各数据源采集器测试
│
└── utils/                               # 工具模块
    ├── __init__.py
    └── date_utils.py                    # 日期工具函数（交易日判断、日期格式化等）
```

**角色定位**：系统的数据入口 — ✅ 已完工。从 6 个外部数据源（腾讯、同花顺、百度、通达信 TCP、AKShare）采集实时行情、K 线、资金流向、龙虎榜等数据，通过工厂模式的故障转移机制保证采集可靠性。已重构为**适配器(Adapter) + 管道(Pipeline) + 存储(Storage)**三层架构，新增并行采集编排器(Orchestrator)实现 16 种数据类型的分组并发采集，多周期 K 线采集支持 8 种频率（1min~月K），资讯层覆盖新闻/研报/一致预期/公告。输出到 CSV/JSON 本地存档，并通过统一存储管理器同步至 MySQL 和 HDFS。

---

### 2.2 `bigdata-processing/` — 大数据处理层 (SQL / Spark / MapReduce) — ✅ 已完工

```
bigdata-processing/
├── batch/
│   ├── run_batch_pipeline.py            # ★ 批处理管道调度器（daily/incremental/rebuild 模式）
│   └── __init__.py
│
├── hive/                                 # ★ Hive 数据仓库（离线分析）
│   ├── ddl/                              # 建表语句（DDL）— 7 个文件
│   │   ├── stock_basic.sql               #   股票基础信息外部表
│   │   ├── stock_daily_partitioned.sql   #   日 K 线分区外部表
│   │   ├── stock_daily_orc.sql           #   ★ ORC 格式优化表（比 TEXTFILE 快 5~15x）
│   │   ├── fund_nav.sql                  #   基金净值外部表
│   │   ├── signal_tables.sql             #   信号数据外部表（题材、龙虎榜、北向等）
│   │   ├── precomputed_results.sql       #   预计算结果表
│   │   └── recovery_checkpoint.sql       #   恢复检查点表
│   ├── dml/                              # 数据分析查询（DML）— 8 个文件
│   │   ├── analysis_daily.sql            #   日均价统计
│   │   ├── analysis_change.sql           #   涨跌幅统计排行
│   │   ├── analysis_correlation.sql      #   Pearson 相关系数计算
│   │   ├── analysis_technical.sql        #   MA / RSI 技术指标 SQL 计算
│   │   ├── analysis_year_comparison.sql  #   年同比分析
│   │   ├── analysis_signal_fusion.sql    #   信号融合分析
│   │   ├── load_data.sql                 #   数据加载（外部表 → 内部表）
│   │   └── partition_manage.sql          #   分区管理（MSCK / ADD / DROP）
│   └── udf/                              # Hive UDF 自定义函数（新增 5 个）
│       └── [extract_code, classify_change, ...]  # 新增 UDF 函数
│
├── mapreduce/                            # MapReduce 遗留计算（Java）
│   ├── pom.xml                           #   Maven 项目配置
│   └── src/
│       ├── main/java/com/stock/mr/
│       │   ├── IndustryStatsMR.java       #   行业统计（按行业聚合涨跌幅）
│       │   ├── MonthlyReturnMR.java       #   月收益率计算
│       │   ├── StockYearlyReturn.java     #   年收益率计算
│       │   ├── TechnicalIndicatorMR.java  #   技术指标计算
│       │   └── VolumeAnalysis.java        #   成交量分析
│       └── test/java/com/stock/mr/
│           ├── StockYearlyReturnTest.java
│           └── VolumeAnalysisTest.java
│
├── spark/                                # ★ Spark 分布式计算（主力引擎）
│   ├── batch/                            # 批处理 Jobs — 8 个文件
│   │   ├── yearly_return.py              #   年收益率排名
│   │   ├── monthly_return.py             #   月收益率排名
│   │   ├── ma_trend.py                   #   均线金叉/死叉信号检测
│   │   ├── correlation.py                #   相关系数矩阵计算
│   │   ├── sector_ranking.py             #   行业涨跌排行
│   │   ├── filter_stocks.py              #   PE/PB/ROE 多条件筛选（共享 spark_config）
│   │   ├── trend_judge.py                #   趋势判断（上升/下跌/震荡）
│   │   └── stock_predictor.py            #   ★ [新增] MLlib 股票预测原型
│   ├── sql/
│   │   └── hive_query.py                 #   Spark SQL 查询 Hive 工具
│   ├── mllib/                            #   MLlib 机器学习（新增）
│   └── streaming/
│       └── realtime_indicator.py         #   流式计算：实时指标更新
│
├── scripts/                              # ★ 运维脚本（新增）
│   ├── migrate_hive_to_orc.py            #   Hive TEXTFILE → ORC 一键迁移
│   └── [其他脚本]
│
└── backup/                               # ★ HDFS 备份管道（新增）
    └── hdfs_backup.py                    #   HDFS 全量/增量备份 + 自动清理
```

**角色定位**：系统的"数据炼油厂" — ✅ 已完工。接收 L1 采集的原始数据后，依次执行 Hive SQL 分析 → Spark 批处理计算 → （可选）MapReduce 传统计算，将原始数据加工为预计算分析结果，供后端 API 查询使用。已完成 ORC 格式优化（10x+ 查询性能提升）、Spark 共享配置模块消除重复代码、数据质量检查(Data Quality Check)门禁、HDFS 备份管道（全量+增量+自动清理），新增 MLlib 股票预测原型和 5 个 Hive UDF。

---

### 2.3 `analysis-algorithms/` — 算法分析层 (Python) ⬅ 当前开发焦点

```
analysis-algorithms/
├── __init__.py                          # 模块初始化
├── analysis_orchestrator.py             # ★ 分析编排引擎（数据加载+技术指标+信号+缠论+量化）
├── pytest.ini                           # 测试配置
├── requirements.txt                     # 依赖包列表
│
├── technical/                           # ★ 技术指标计算
│   ├── __init__.py
│   ├── ma.py                            #   均线 (MA5/10/20/60) + 金叉/死叉检测
│   ├── macd.py                          #   MACD (EMA12/26, DIF, DEA) + 背离识别
│   ├── kdj.py                           #   KDJ (RSV, K/D/J) + 超买/超卖判断
│   ├── rsi.py                           #   RSI (6/12/24) + Wilders 平滑算法
│   └── bollinger.py                     #   布林带 (中轨/上轨/下轨/带宽/%B)
│
├── chanlun/                             # ★ 缠论分析（6 步递归分解）
│   ├── __init__.py
│   ├── fractal.py                       #   Step 2: 分型识别（顶分型/底分型）
│   ├── pen.py                           #   Step 3: 笔识别（上升笔/下降笔）
│   ├── segment.py                       #   Step 4: 线段识别（至少3笔构成）
│   ├── central.py                       #   Step 5: 中枢识别（ZG / ZD 区间计算）
│   ├── signal.py                        #   Step 6: 买卖信号（三类买点/卖点）
│   ├── analyzer.py                      #   缠论分析器：编排 6 步递归全流程
│   └── visualizer.py                    #   缠论可视化（绘制分型、笔、线段、中枢）
│
├── quantitative/                        # ★ 量化策略 & 回测
│   ├── __init__.py
│   ├── strategy_base.py                 #   策略基类（定义策略接口）
│   ├── ma_strategy.py                   #   均线策略（金叉买入/死叉卖出）
│   ├── momentum_strategy.py             #   动量策略（动量因子选股）
│   ├── multi_factor_strategy.py         #   多因子策略（多因子评分选股）
│   └── backtest.py                      #   回测引擎（总收益率/年化/最大回撤/夏普比率/胜率）
│
├── tests/                               # 单元测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_technical.py                #   技术指标测试
│   └── test_chanlun.py                  #   缠论分析测试
│
└── utils/
    ├── __init__.py
    └── data_loader.py                   # 数据加载工具（读取 CSV / MySQL 数据）
```

---

### 2.4 `backend/` — 后端 API 层 (Spring Boot 3 + Java 17)

```
backend/
├── pom.xml                              # Maven 项目配置（Spring Boot、MyBatis-Plus、Redis 等）
│
└── src/
    ├── main/
    │   ├── java/com/stock/
    │   │   ├── StockApplication.java    # Spring Boot 启动入口
    │   │   │
    │   │   ├── config/                  # ★ 应用配置
    │   │   │   ├── AppConfig.java       #   通用 Bean 配置（RestTemplate、线程池等）
    │   │   │   ├── MyBatisPlusConfig.java # MyBatis-Plus 分页插件 & 配置
    │   │   │   ├── MyMetaObjectHandler.java # 自动填充 created_at / updated_at
    │   │   │   ├── RedisConfig.java     #   Redis 缓存管理（TTL=30min, Jackson 序列化）
    │   │   │   ├── WebMvcConfig.java    #   Web MVC 配置（CORS、拦截器等）
    │   │   │   └── WebSocketConfig.java #   WebSocket 实时行情推送配置
    │   │   │
    │   │   ├── controller/              # ★ REST 控制器（9 个）
    │   │   │   ├── StockController.java #   股票 API（列表/详情/K线/搜索/行业）
    │   │   │   ├── FundController.java  #   基金 API（列表/详情/净值/持仓）
    │   │   │   ├── AnalysisController.java # 分析 API（收益率/趋势/筛选/相关性/板块排行）
    │   │   │   ├── SignalDataController.java # 信号 API（题材/龙虎榜/北向/解禁/行业对比）
    │   │   │   ├── UserController.java  #   用户 API（登录/注册/信息）
    │   │   │   ├── WatchlistController.java # 自选 API（列表/添加/删除）
    │   │   │   ├── IndexController.java #   指数 API（列表/详情/K线）
    │   │   │   ├── AiDialogueController.java # AI 对话代理（转发到 AI 服务）
    │   │   │   └── SecurityController.java # 安全配置管理 API
    │   │   │
    │   │   ├── dto/                     # 数据传输对象
    │   │   │   ├── AIRequest.java       #   AI 对话请求体
    │   │   │   ├── AIResponse.java      #   AI 对话响应体
    │   │   │   └── ChatMessage.java     #   聊天消息体
    │   │   │
    │   │   ├── entity/                  # ★ 数据实体（16 张业务表映射）
    │   │   │   ├── User.java            #   用户表
    │   │   │   ├── Stock.java           #   股票信息表
    │   │   │   ├── StockDaily.java      #   日 K 线数据表
    │   │   │   ├── Fund.java            #   基金信息表
    │   │   │   ├── FundNav.java         #   基金净值表
    │   │   │   ├── FundHolding.java     #   基金持仓表
    │   │   │   ├── MarketIndex.java     #   市场指数表
    │   │   │   ├── IndexDaily.java      #   指数日线表
    │   │   │   ├── Watchlist.java       #   用户自选表
    │   │   │   ├── AnalysisResult.java  #   分析结果表
    │   │   │   ├── PrecomputedResult.java # 预计算结果表
    │   │   │   ├── SignalHotReason.java #   题材归因信号表
    │   │   │   ├── SignalDragonTiger.java # 龙虎榜信号表
    │   │   │   ├── SignalNorthbound.java #  北向资金信号表
    │   │   │   ├── SignalLockup.java    #   限售解禁信号表
    │   │   │   ├── SignalDailyIndustry.java # 行业日数据表
    │   │   │   └── AiChat.java          #   AI 对话记录表
    │   │   │
    │   │   ├── mapper/                  # ★ MyBatis 数据映射器（17 个）
    │   │   │   ├── StockMapper.java ~ WatchlistMapper.java
    │   │   │   └── ... （每个实体对应一个 Mapper 接口）
    │   │   │
    │   │   ├── service/                 # ★ 业务逻辑层
    │   │   │   ├── StockService.java    #   股票业务接口
    │   │   │   ├── FundService.java     #   基金业务接口
    │   │   │   ├── AnalysisService.java #   分析业务接口
    │   │   │   ├── AIDialogueService.java # AI 对话业务接口
    │   │   │   ├── UserService.java     #   用户业务接口
    │   │   │   ├── WatchlistService.java #  自选业务接口
    │   │   │   ├── StockDailyService.java # K线数据业务接口
    │   │   │   ├── IndexService.java    #   指数业务接口
    │   │   │   └── impl/                #   接口实现类（8 个 ServiceImpl）
    │   │   │       ├── StockServiceImpl.java
    │   │   │       └── ...（每个接口一个实现）
    │   │   │
    │   │   ├── security/                # ★ 安全认证框架
    │   │   │   ├── SecurityConfig.java  #   Spring Security 配置（JWT、白名单、CORS）
    │   │   │   ├── JwtUtil.java         #   JWT 令牌工具（生成/验证/解析）
    │   │   │   ├── JwtFilter.java       #   JWT 认证过滤器（OncePerRequestFilter）
    │   │   │   ├── PasswordPolicyValidator.java # 密码策略校验器
    │   │   │   ├── Permission.java      #   权限枚举定义
    │   │   │   ├── PermissionInterceptor.java # 权限拦截器
    │   │   │   ├── RequirePermission.java    # 权限注解（AOP 切面）
    │   │   │   ├── SecurityLevelService.java # 安全等级服务
    │   │   │   └── UserRole.java        #   用户角色枚举
    │   │   │
    │   │   ├── vo/                      # 视图对象（预留）
    │   │   │
    │   │   └── websocket/
    │   │       └── StockWebSocketHandler.java # WebSocket 推送（实时行情）
    │   │
    │   └── resources/                   # 应用资源
    │       ├── application.yml          # ★ 主配置（数据源、Redis、AI 服务地址）
    │       ├── mapper/                  # MyBatis XML 映射文件（12 个 SQL XML）
    │       │   ├── StockMapper.xml
    │       │   ├── StockDailyMapper.xml
    │       │   ├── FundMapper.xml
    │       │   └── ...（复杂查询写在 XML 中）
    │       └── security/                # 安全凭据
    │           ├── credentials.json     #   应用用户账户凭据
    │           ├── security-accounts.json #  安全账户配置
    │           └── security-levels.yml  #   多级安全策略配置
    │
    └── test/                            # 后端单元测试
```

**角色定位**：系统的业务中枢。基于 Spring Boot 3 + MyBatis-Plus 构建的 RESTful API 服务，提供股票、基金、分析、信号、用户、自选等 8 大业务模块。集成 JWT 无状态认证、Redis 缓存（TTL=30min）、WebSocket 实时推送、Web MVC 拦截器，通过 `@Cacheable` 实现高频接口缓存加速。

---

### 2.5 `ai-service/` — AI 智能服务层 (FastAPI + Python)

```
ai-service/
├── .env.example                        # 环境变量模板（DeepSeek API Key、后端地址等）
├── requirements.txt                    # Python 依赖包
│
└── app/
    ├── __init__.py
    ├── config.py                       # 配置加载（环境变量解析）
    ├── main.py                         # ★ FastAPI 应用入口（路由注册、中间件、启动事件）
    │
    ├── agents/                         # ★ 7 个 AI 智能体
    │   ├── __init__.py
    │   ├── base_agent.py               #   智能体基类（定义 chat/analyze 接口）
    │   ├── fundamentals_analyst.py     #   Agent 1: 基本面分析（PE/PB/市值/盈利能力）
    │   ├── technical_analyst.py        #   Agent 2: 技术分析（K线/均线/MACD/RSI/KDJ/布林带）
    │   ├── sentiment_analyst.py        #   Agent 3: 情绪分析（题材热度/北向资金/主力资金）
    │   ├── news_analyst.py             #   Agent 4: 新闻分析（新闻/公告/研报事件驱动）
    │   ├── researcher_team.py          #   Agent 5: 研究员辩论小组（3轮多Agent辩论）
    │   ├── trader_agent.py             #   Agent 6: 交易决策（买入/卖出/持有 + 仓位 + 止损）
    │   └── risk_manager.py             #   Agent 7: 风控审核（风险评级 + 最终裁定）
    │
    ├── api/                            # API 路由层
    │   ├── __init__.py
    │   └── dialogue.py                 #   /api/ai/chat 对话接口 & /health 健康检查
    │
    ├── fusion/                         # 多源数据融合（预留）
    │   └── __init__.py
    │
    ├── models/                         # ★ AI 模型客户端
    │   ├── __init__.py
    │   ├── model_registry.py           #   模型注册中心（管理多模型接入）
    │   ├── deepseek_client.py          #   DeepSeek API 客户端（HTTPS 调用）
    │   └── simulation.py               #   模拟回复引擎（无 API Key 时的降级策略）
    │
    ├── services/                       # ★ 核心业务服务
    │   ├── __init__.py
    │   ├── dialogue_service.py         #   对话服务（构建上下文 → 调用 AI → 返回回复）
    │   ├── multi_agent_service.py      #   多智能体深度分析（编排 7 Agent 流水线）
    │   └── memory_service.py           #   记忆服务（历史决策保存 + 自动反思对比）
    │
    └── utils/                          # 工具模块
        └── __init__.py

└── tests/
    ├── conftest.py                     # 测试夹具
    └── test_agents.py                  # 智能体单元测试
```

**角色定位**：系统的"智囊大脑"。基于 FastAPI 构建的 AI 微服务，采用多智能体架构（7 个专业化 Agent 顺序执行），支持 DeepSeek API 实时分析 和 无 Key 模拟模式 两种工作方式，具备自动降级能力。通过 httpx 异步并行调用后端 3 个 API 获取实时数据上下文，提供智能对话与深度分析能力。

---

### 2.6 `frontend/` — 前端展示层 (Vue 3 + TypeScript)

```
frontend/
├── package.json                        # npm 项目配置
├── vite.config.ts                      # Vite 构建配置 + 开发代理（/api → localhost:8082）
├── tsconfig.json                       # TypeScript 编译配置
├── index.html                          # 入口 HTML
│
└── src/
    ├── main.ts                         # 应用入口（挂载 Vue、Pinia、Router）
    ├── App.vue                         # 根组件
    │
    ├── api/                            # ★ API 封装层（Axios 实例 + 各模块 API）
    │   ├── request.ts                  #   Axios 实例（baseURL=/api, 15s 超时, JWT 拦截器）
    │   ├── stock.ts                    #   股票模块 API
    │   ├── fund.ts                     #   基金模块 API
    │   ├── analysis.ts                 #   分析模块 API
    │   ├── signal.ts                   #   信号模块 API
    │   ├── user.ts                     #   用户模块 API
    │   ├── watchlist.ts                #   自选模块 API
    │   ├── ai.ts                       #   AI 对话模块 API
    │   ├── index.ts                    #   指数模块 API
    │   └── types.ts                    #   API 请求/响应类型定义
    │
    ├── assets/                         # 静态资源
    │   ├── icons/                      #   图标库
    │   ├── images/                     #   图片资源
    │   └── styles/                     #   全局样式
    │
    ├── components/                     # ★ 可复用组件
    │   ├── common/                     #   通用组件
    │   │   ├── AppHeader.vue           #     顶栏导航
    │   │   ├── AppLayout.vue           #     页面布局框架
    │   │   └── AlertBell.vue           #     消息通知铃铛
    │   ├── chart/                      #   图表组件
    │   │   ├── KLineChart.vue          #     K 线图（ECharts）
    │   │   └── TreemapChart.vue        #     板块云图（ECharts）
    │   └── ai/                         #   AI 相关组件
    │       ├── AiChatPanel.vue         #     AI 对话面板
    │       └── AiSignalSummary.vue     #     AI 信号摘要
    │
    ├── views/                          # ★ 页面视图（18 个路由页面）
    │   ├── HomeView.vue                #   首页大盘（指数轮播、板块云图、资金流向）
    │   ├── StockListView.vue           #   股票列表（搜索、行业筛选、排序、分页）
    │   ├── StockDetailView.vue         #   个股详情（K线、技术指标、缠论、AI分析）
    │   ├── FundListView.vue            #   基金列表
    │   ├── FundDetailView.vue          #   基金详情（净值走势、持仓明细）
    │   ├── PortfolioView.vue           #   持仓管理
    │   ├── WatchlistView.vue           #   自选列表
    │   ├── ChatView.vue                #   AI 智能对话
    │   ├── HotReasonView.vue           #   题材热点
    │   ├── DragonTigerView.vue         #   龙虎榜
    │   ├── NorthboundView.vue          #   北向资金
    │   ├── LockupView.vue              #   限售解禁
    │   ├── IndustryCompareView.vue     #   行业对比
    │   ├── SectorDetailView.vue        #   行业详情
    │   ├── IndexDetailView.vue         #   指数详情
    │   ├── NewsView.vue                #   实时新闻
    │   ├── ConsensusEpsView.vue        #   一致预期
    │   ├── FundFlowView.vue            #   资金流向
    │   └── LoginView.vue               #   登录/注册
    │
    ├── router/
    │   └── index.ts                    # Vue Router 路由配置（19 条路由）
    │
    ├── stores/                         # ★ Pinia 状态管理
    │   ├── user.ts                     #   用户状态（登录/登出、Token 管理）
    │   └── stock.ts                    #   股票状态（列表缓存、筛选条件）
    │
    ├── styles/                         # 样式定义
    │   ├── variables.scss              #   SCSS 变量（颜色、字体、间距）
    │   └── global.scss                 #   全局样式
    │
    ├── types/                          # TypeScript 类型定义
    │   └── index.ts                    #   全局类型（Stock, Fund, Kline 等）
    │
    ├── utils/                          # 工具函数
    │   ├── format.ts                   #   格式化工具（金额、百分比、日期）
    │   └── indicators.ts              #   前端指标计算辅助函数
    │
    ├── i18n/                           # 国际化（预留）
    │   └── index.ts
    │
    └── __tests__/                      # 前端单元测试
        ├── env.d.ts
        ├── setup.ts
        ├── api/
        │   └── request.test.ts
        └── stores/
            ├── stock.test.ts
            └── user.test.ts
```

**角色定位**：用户交互界面。基于 Vue 3 + TypeScript + Pinia 构建的单页应用（SPA），通过 ECharts 实现丰富的金融数据可视化（K 线图、板块云图、资金流向图等），Element Plus 提供 UI 组件库。覆盖股票浏览、基金查询、技术分析、AI 对话、信号监控等 19 个功能页面，支持 JWT Token 自动注入与 401 自动跳转。

---

### 2.7 `docker/` — 容器化部署配置

```
docker/
├── .env.dev                            # 开发环境变量
├── docker-compose.yml                  # ★ 主编排文件（13 个容器定义）
├── docker-compose.dev.yml              # 开发环境覆盖配置
├── README.md                           # 部署说明
│
├── frontend/                           # 前端容器
│   ├── Dockerfile                      #   生产构建（Nginx 静态托管）
│   ├── Dockerfile.dev                  #   开发构建（热重载）
│   └── nginx.conf                      #   Nginx 反向代理配置（/ → 前端, /api/ → 后端, /ai/ → AI）
│
├── backend/                            # 后端容器
│   ├── Dockerfile                      #   生产构建（Java 17 运行）
│   └── Dockerfile.dev                  #   开发构建
│
├── ai-service/                         # AI 服务容器
│   ├── Dockerfile                      #   生产构建（Python 3.11 运行）
│   └── Dockerfile.dev                  #   开发构建
│
├── mysql/                              # MySQL 数据库
│   ├── init.sql                        #   ★ 初始化脚本（建库、建16张表、插示例数据）
│   └── migrate.sql                     #   数据库迁移脚本
│
├── hadoop/                             # Hadoop 配置
│   ├── core-site.xml                   #   HDFS 核心配置
│   ├── hdfs-site.xml                   #   HDFS 数据块/副本配置
│   ├── mapred-site.xml                 #   MapReduce 配置
│   └── yarn-site.xml                   #   YARN 资源调度配置
│
├── hive/                               # Hive 数据仓库
│   ├── conf/
│   │   └── hive-site.xml               #   Hive 配置（Metastore、Server2）
│   ├── hive-site.xml                   #   Hive 配置（完整版）
│   ├── entrypoint-wrapper.sh           #   容器启动包装脚本
│   └── lib/
│       └── mysql-connector-j-8.0.33.jar # MySQL JDBC 驱动（Hive Metastore 用）
│
└── spark/
    └── spark-defaults.conf             # Spark 默认配置（内存、核心数、序列化）
```

**角色定位**：一键部署的"启动钥匙"。通过 Docker Compose 编排 13 个容器（前端 Nginx、后端 Spring Boot、AI FastAPI、MySQL、Redis、HDFS × 4、YARN × 2、Hive、Spark × 2），实现全栈一键部署。提供生产/开发双模式 Dockerfile，Nginx 统一反向代理入口，Hadoop 全套配置文件。

---

### 2.8 `scripts/` — 实用工具脚本

```
scripts/
├── e2e_verify.py                       # 端到端验证脚本（检查 11 项：目录结构、依赖、API、HDFS 等）
├── gen_seed.py                         # 种子数据生成器（生成测试用股票/K线数据）
├── seed_stock_daily.sql                # 股票日线种子数据 SQL
├── run-all-tests.bat                   # Windows 全量测试运行
├── run-all-tests.sh                    # Linux 全量测试运行
├── start-all.sh                        # 一键启动所有服务
└── stop-all.sh                         # 一键停止所有服务
```

**角色定位**：开发运维工具箱。提供一键验证、测试运行、种子数据生成、服务启停等常用操作脚本。

---

## 三、数据目录与日志

| 目录 | 说明 |
|:-----|:------|
| `data/` | Docker 持久化数据卷挂载点（MySQL 数据文件、HDFS 元数据等） |
| `logs/` | 运行日志目录 |
| `docs/` | 项目技术文档 |

---

## 四、架构层级总览

```
L6 前端展示层    frontend/   (Vue 3 + TypeScript + ECharts + Element Plus)
    ↑ Axios /api/ & /ai/
L5 AI 智能层     ai-service/ (FastAPI + 7 Agent 多智能体 + DeepSeek)
    ↑ httpx 调用后端 API
L4 后端 API 层   backend/    (Spring Boot 3 + MyBatis-Plus + Redis + JWT)
    ↑ JDBC / Redis / 算法分析读取
L3 算法分析层    analysis-algorithms/ (Python 原生: 技术指标 + 缠论 + 量化策略 + 分析引擎) ⬅ 当前焦点
    ↑ 数据读取（MySQL 预计算结果）
L2 大数据处理层  bigdata-processing/ (Hive SQL + Spark + MapReduce) ✅ 已完工
    ↑ HDFS / MySQL
L1 数据采集层    data-collector/ (Python: 6数据源 + 适配器 + 管道 + 存储) ✅ 已完工
```

**数据流向**：采集层(L1) → 原始数据(CSV/JSON) → 存储(MySQL + HDFS) → 大数据处理层(L2) → 预计算结果 → 算法分析层(L3) → 后端 API(L4) → 前端(L6) / AI 服务(L5)

**状态说明**：
- ✅ **L1 数据采集层** — 已完工（适配器+管道+存储三层重构，运行稳定）
- ✅ **L2 大数据处理层** — 已完工（ORC 优化、共享配置、数据质量检查、备份管道）
- ⬅ **L3 算法分析层** — 当前开发焦点（分析引擎编排 + 链路打通）
- 🔧 L4~L6 — 已有基础实现，持续迭代优化

**故障降级机制**：
- 数据源故障：工厂模式自动切换优先级
- AI API Key 缺失：自动切换到模拟回复模式
- HDFS/Hive 不可用：跳过不影响核心功能
- Redis 不可用：缓存穿透直接查询 MySQL
- 后端 API 超时：AI 服务跳过该数据源继续响应
