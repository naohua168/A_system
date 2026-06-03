# 项目目录结构说明文档

> **文档版本**: V2.2  
> **更新日期**: 2026-06-03  
> **项目名称**: 智能分析系统 (A_system)  
> **变更摘要**: v4.2 移除基金/板块详情/一致预期 3 模块；全部信号视图重写；HomeView 三次迭代；云图成分股移除（外网不可达）；auto_seed treemap camelCase 改造；数据过期/路由白屏/缠论不显示修复。

---

## 一、项目全景图

```
A_system/
├── ai-service/                          # L5 - AI 智能服务层 ✅
├── analysis-algorithms/                 # L3 - 算法分析层 ✅
├── backend/                             # L4 - 后端 API 服务层 ✅
├── bigdata-processing/                  # L2 - 大数据处理层 ✅
├── data-collector/                      # L1 - 数据采集层 ✅
├── data/                                # 数据持久化目录 (Docker Volume)
├── docker/                              # Docker 容器化部署配置
├── docs/                                # 项目文档
├── frontend/                            # L6 - 前端展示层 ✅
├── logs/                                # 运行日志目录
├── scripts/                             # 实用工具脚本
├── LICENSE                              # MIT 开源许可证
└── README.md                            # 项目总览说明
```

> **状态说明**: L1~L6 全部六层均已完工，当前处于持续迭代优化阶段。

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
│   ├── base_collector.py                # 采集器基类（定义采集接口、CSV 写入、重试机制、熔断器）
│   ├── tencent_collector.py             # 腾讯财经 → 实时行情 / PE / PB / 市值 (HTTP, 优先级9)
│   ├── ths_hot_collector.py             # 同花顺 → 强势股题材归因 (HTTP, 优先级8)
│   ├── ths_northbound_collector.py      # [新增] 同花顺 → 北向资金分钟流向
│   ├── baidu_collector.py               # 百度股市通 → 概念板块 / 资金流向 (HTTP, 优先级7)
│   ├── mootdx_collector.py              # 通达信 TCP → K 线 / 五档盘口 / 逐笔 / F10 (TCP, 优先级10)
│   ├── akshare_extended_collector.py    # AKShare → 龙虎榜 / 解禁 / 行业 / 研报 (HTTP, 优先级6)
│   ├── kline_collector.py               # ★ 多周期 K 线采集器（8 种周期：1min~月K）
│   ├── information_collector.py         # [新增] 资讯层采集器（研报/新闻/公告/一致预期）
│   └── stock_list.py                    # ★ 全市场股票代码源（腾讯扫描 + 缓存）
│
├── adapters/                            # ★ 适配器层（全新重构）
│   ├── __init__.py
│   ├── base_adapter.py                  # 适配器基类/协议（AdapterMetadata, AdapterRegistry）
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
├── scheduler/                           # 调度器
│   ├── __init__.py
│   ├── market_collect.py                # 主调度入口：按模式（全量/增量/独立）执行采集
│   └── run_collector.py                 # 单次采集执行器（调用工厂采集并返回 DataFrame）
│
├── sql/                                 # ★ SQL DDL 定义
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
│       ├── extract_code.py               #   从字符串提取股票代码
│       ├── classify_change.py            #   涨跌幅分类
│       └── ...                           #   其他自定义 UDF
│
├── mapreduce/                            # MapReduce 遗留计算（Java）
│   ├── pom.xml                           #   Maven 项目配置
│   └── src/
│       ├── main/java/com/stock/mr/
│       │   ├── IndustryStatsMR.java       #   [优化] 行业统计（改用 DistributedCache 加载行业映射，保留硬编码回退）
│       │   ├── MonthlyReturnMR.java       #   月收益率计算
│       │   ├── StockYearlyReturn.java     #   年收益率计算
│       │   ├── TechnicalIndicatorMR.java  #   技术指标计算
│       │   └── VolumeAnalysis.java        #   成交量分析
│       └── test/java/com/stock/mr/
│           ├── IndustryStatsMRTest.java   #   [新增] 行业统计测试（CSV解析/映射加载/聚合计算）
│           ├── StockYearlyReturnTest.java
│           └── VolumeAnalysisTest.java
│
├── spark/                                # ★ Spark 分布式计算（主力引擎）
│   ├── spark_config.py                   # ★ [新增] 统一 Spark 配置模块（消除 7 处重复）
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
│   ├── export_industry_mapping.py        #   [新增] 行业映射 CSV 导出（从 MySQL/Hive → DistributedCache）
│   ├── migrate_hive_to_orc.py            #   Hive TEXTFILE → ORC 一键迁移
│   └── init_kafka_topics.sh              #   [新增] 初始化 Kafka Topic
│
├── backup/                               # ★ HDFS 备份管道（新增）
│   └── hdfs_backup.py                    #   HDFS 全量/增量备份 + 自动清理
│
└── streaming/                            # [新增] Spark Structured Streaming 管道
    └── market_streaming.py               #   实时行情流式处理
```

**角色定位**：系统的"数据炼油厂" — ✅ 已完工。接收 L1 采集的原始数据后，依次执行 Hive SQL 分析 → Spark 批处理计算 → （可选）MapReduce 传统计算，将原始数据加工为预计算分析结果，供后端 API 查询使用。已完成 ORC 格式优化（10x+ 查询性能提升）、Spark 共享配置模块消除重复代码、数据质量检查(Data Quality Check)门禁、HDFS 备份管道（全量+增量+自动清理），新增 MLlib 股票预测原型和 5 个 Hive UDF。

---

### 2.3 `analysis-algorithms/` — 算法分析层 (Python) — ✅ 已完工

> **状态变更**: V2.0 更新 — 所有模块已完成，不再是开发中焦点。

```
analysis-algorithms/
├── __init__.py                          # 模块初始化，导出 analyze/rank 接口
├── requirements.txt                     # 依赖包列表
│
├── engine/                              # ★ 分析编排引擎（重构后新增目录）
│   ├── __init__.py                      #   导出 AnalysisEngine, ResultStore
│   ├── orchestrator.py                  #   ★ 核心引擎：分析编排（并行加载→技术指标→缠论→量化→持久化）
│   └── result_store.py                  #   结果持久化（MySQL REPLACE INTO + Redis 缓存）
│
├── data/                                # ★ 数据层（重构后新增）
│   ├── __init__.py                      #   导出 DataLoader
│   ├── loader.py                        #   MySQL 连接池 + Redis 缓存 + 并行信号读取
│   └── models.py                        #   数据契约（KlineRecord, RealtimeQuote, Precomputed*）
│
├── technical/                           # ★ 技术指标计算
│   ├── __init__.py
│   ├── ma.py                            #   均线 (MA) + 金叉/死叉检测
│   ├── macd.py                          #   MACD (EMA12/26, DIF, DEA) + 背离识别
│   ├── kdj.py                           #   KDJ (RSV, K/D/J) + 超买/超卖判断
│   ├── rsi.py                           #   RSI (6/12/24) + Wilders 平滑算法
│   ├── bollinger.py                     #   布林带 (中轨/上轨/下轨/带宽/%B)
│   ├── cci.py                           #   [新增] 商品通道指数 CCI
│   ├── wr.py                            #   [新增] 威廉指标 W%R
│   ├── obv.py                           #   [新增] 能量潮 OBV
│   └── volume.py                        #   [新增] 成交量均线 + 量比
│
├── chanlun/                             # ★ 缠论分析（6 步递归分解）
│   ├── __init__.py
│   ├── fractal.py                       #   Step 1-2: K线包含处理 + 分型识别（顶分型/底分型）
│   ├── pen.py                           #   Step 3: 笔识别（上升笔/下降笔）
│   ├── segment.py                       #   Step 4: 线段识别（至少3笔构成）
│   ├── central.py                       #   Step 5: 中枢识别（ZG / ZD 区间计算）
│   ├── signal.py                        #   Step 6: 买卖信号（三类买点/卖点）
│   ├── analyzer.py                      #   缠论分析器：编排 6 步递归全流程
│   └── visualizer.py                    #   缠论可视化（序列化 → JSON 供前端渲染）
│
├── quantitative/                        # ★ 量化策略 & 回测
│   ├── __init__.py
│   ├── strategy_base.py                 #   策略基类 + 策略引擎（StrategyEngine）
│   ├── ma_strategy.py                   #   均线策略（金叉买入/死叉卖出）
│   ├── momentum_strategy.py             #   动量策略（动量因子选股）
│   ├── multi_factor_strategy.py         #   多因子策略（多因子评分选股）
│   └── backtest.py                      #   回测引擎（总收益率/年化/最大回撤/夏普比率/胜率）
│
├── tests/                               # 单元测试
│   ├── conftest.py
│   ├── test_technical.py                #   技术指标测试（14 个用例）
│   ├── test_chanlun.py                  #   缠论分析测试（7 个用例）
│   └── test_orchestrator.py             #   [新增] 编排引擎测试
│
└── utils/
    └── data_loader.py                   # 数据加载工具（读取 CSV / MySQL 数据）
```

**角色定位**：系统的"分析大脑" — ✅ 已完工。基于 Python 原生实现的综合分析引擎，由 `AnalysisEngine` 统一编排：并行加载 K 线+行情 → 5 个技术指标计算（预计算优先/本地计算回退）→ 5 种信号并行读取 → 缠论 6 步流水线 → 量化策略运行 → 结果持久化到 MySQL + Redis 缓存。支持批量分析、全市场排名，完整覆盖技术指标、缠论、量化三大分析领域。

---

### 2.4 `backend/` — 后端 API 层 (Spring Boot 3 + Java 17) — ✅ 已完工

> **版本修正**: V2.0 — 此前文档误标为 Spring Boot 2.7.18，实际为 Spring Boot 3.x (jakarta.* 命名空间)。

```
backend/
├── pom.xml                              # Maven 项目配置（Spring Boot 3、MyBatis-Plus、Redis 等）
│
└── src/
    ├── main/
    │   ├── java/com/stock/
    │   │   ├── StockApplication.java    # Spring Boot 启动入口
    │   │   │
    │   │   ├── config/                  # ★ 应用配置（7 个文件）
    │   │   │   ├── AppConfig.java       #   通用 Bean 配置（RestTemplate、线程池等）
    │   │   │   ├── MyBatisPlusConfig.java # MyBatis-Plus 分页插件 & 配置
    │   │   │   ├── MyMetaObjectHandler.java # 自动填充 created_at / updated_at
    │   │   │   ├── RedisConfig.java     #   Redis 缓存管理（TTL=30min, Jackson 序列化）
    │   │   │   ├── WebMvcConfig.java    #   Web MVC 配置（CORS、拦截器等）
    │   │   │   ├── WebSocketConfig.java #   WebSocket 实时行情推送配置
    │   │   │   ├── ApiResponseWrapper.java # [新增] 全局响应包装（ResponseBodyAdvice）
    │   │   │   └── GlobalExceptionHandler.java # [V2.0 新增] 全局异常处理器（4 级异常分类+日志）
    │   │   │
    │   │   ├── controller/              # ★ REST 控制器（11 个）
    │   │   │   ├── MarketController.java #   行情 API（列表/详情/K线/搜索/行业/排行/板块K线）
    │   │   │   ├── StockController.java #   [已删除 V2.2] 功能已合并至 MarketController
    │   │   │   ├── FundController.java  #   基金 API（列表/详情/净值/持仓）
    │   │   │   ├── AnalysisController.java # 分析 API（收益率/趋势/筛选/相关性/板块排行/缠论）
    │   │   │   ├── SignalDataController.java # 信号 API（题材/龙虎榜/北向/解禁/行业对比）
    │   │   │   ├── InfoController.java  #   [新增] 资讯 API（研报/新闻/公告/一致预期/PDF）
    │   │   │   ├── IndexController.java #   指数 API（列表/详情/K线）
    │   │   │   ├── UserController.java  #   用户 API（登录/注册/信息）
    │   │   │   ├── WatchlistController.java # 自选 API（列表/添加/删除）
    │   │   │   ├── AiDialogueController.java # AI 对话代理（转发到 AI 服务）
    │   │   │   └── SecurityController.java # 安全配置管理 API
    │   │   │
    │   │   ├── dto/                     # 数据传输对象
    │   │   │   ├── ApiResponse.java     #   ★ 统一响应包装（ok/error/page/notFound/exception）
    │   │   │   ├── AIRequest.java       #   AI 对话请求体
    │   │   │   ├── AIResponse.java      #   AI 对话响应体
    │   │   │   └── ChatMessage.java     #   聊天消息体
    │   │   │
    │   │   ├── entity/                  # ★ 数据实体（23 张业务表映射）
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
    │   │   │   ├── AiChat.java          #   AI 对话记录表
    │   │   │   ├── InfoResearchReport.java # [新增] 券商研报表
    │   │   │   ├── InfoConsensusEps.java #   [新增] 机构一致预期表
    │   │   │   ├── InfoStockNews.java   #   [新增] 个股新闻表
    │   │   │   ├── InfoClsNews.java     #   [新增] 财联社快讯表
    │   │   │   ├── InfoGlobalNews.java  #   [新增] 全球财经资讯表
    │   │   │   ├── InfoFiling.java      #   [新增] 巨潮公告表
    │   │   │   └── InfoPdf.java         #   [新增] 研报 PDF 表
    │   │   │
    │   │   ├── mapper/                  # ★ MyBatis 数据映射器（23 个）
    │   │   │   ├── StockDailyMapper.java  # 含 selectSectorKline [V2.0 新增]
    │   │   │   ├── StockMapper.java ~ WatchlistMapper.java
    │   │   │   └── ... (每个实体对应一个 Mapper 接口)
    │   │   │
    │   │   ├── service/                 # ★ 业务逻辑层（17 个接口 + 18 个实现）
    │   │   │   ├── StockService.java / impl/StockServiceImpl.java
    │   │   │   ├── StockDailyService.java / impl/StockDailyServiceImpl.java
    │   │   │   ├── FundService.java / impl/FundServiceImpl.java
    │   │   │   ├── FundNavService.java / impl/FundNavServiceImpl.java
    │   │   │   ├── FundHoldingService.java / impl/FundHoldingServiceImpl.java
    │   │   │   ├── AnalysisService.java / impl/AnalysisServiceImpl.java # [V2.0 合并缠论]
    │   │   │   ├── SignalDataService.java / impl/SignalDataServiceImpl.java
    │   │   │   ├── IndexService.java / impl/IndexServiceImpl.java
    │   │   │   ├── UserService.java / impl/UserServiceImpl.java
    │   │   │   ├── WatchlistService.java / impl/WatchlistServiceImpl.java
    │   │   │   ├── AIDialogueService.java / impl/AIDialogueServiceImpl.java
    │   │   │   ├── InfoResearchReportService.java / impl/...
    │   │   │   ├── InfoConsensusEpsService.java / impl/...
    │   │   │   ├── InfoStockNewsService.java / impl/...
    │   │   │   ├── InfoClsNewsService.java / impl/...
    │   │   │   ├── InfoGlobalNewsService.java / impl/...
    │   │   │   ├── InfoFilingService.java / impl/...
    │   │   │   ├── InfoReportPdfService.java / impl/...
    │   │   │   └── SecurityLevelService.java / impl/...
    │   │   │
    │   │   ├── security/                # ★ 安全认证框架（8 个文件）
    │   │   │   ├── SecurityConfig.java  #   Spring Security 配置（JWT、白名单、CORS）
    │   │   │   ├── JwtUtil.java         #   JWT 令牌工具（生成/验证/解析）
    │   │   │   ├── JwtFilter.java       #   JWT 认证过滤器（OncePerRequestFilter）
    │   │   │   ├── PasswordPolicyValidator.java # 密码策略校验器
    │   │   │   ├── Permission.java      #   权限枚举定义
    │   │   │   ├── PermissionInterceptor.java # 权限拦截器
    │   │   │   ├── RequirePermission.java    # 权限注解（AOP 切面）
    │   │   │   └── SecurityLevelService.java # 安全等级服务
    │   │   │
    │   │   └── websocket/
    │   │       └── StockWebSocketHandler.java # WebSocket 推送（实时行情）
    │   │
    │   └── resources/                   # 应用资源
    │       ├── application.yml          # ★ 主配置（数据源、Redis、AI 服务地址）
    │       ├── mapper/                  # MyBatis XML 映射文件（12 个 SQL XML）
    │       │   ├── StockDailyMapper.xml # 含 selectSectorKline [V2.0 新增]
    │       │   ├── StockMapper.xml
    │       │   └── ...（复杂查询写在 XML 中，简单查询靠 MyBatis-Plus 自动）
    │       └── security/
    │           ├── credentials.json     #   系统凭据总览
    │           ├── security-accounts.json # 用户种子数据
    │           └── security-levels.yml  #   多级安全策略配置
    │
    └── test/                            # 后端单元测试（31 个用例）
        ├── AnalysisServiceImplTest.java # 16 用例
        ├── AnalysisControllerTest.java  # 10 用例
        └── StockControllerTest.java     # 5 用例
```

**角色定位**：系统的业务中枢 — ✅ 已完工。基于 Spring Boot 3 + MyBatis-Plus 构建的 RESTful API 服务，提供股票、基金、分析、信号、资讯、用户、自选等 12 大业务模块。集成 JWT 无状态认证、Redis 缓存（TTL=30min）、WebSocket 实时推送、全局异常处理器（4 级异常分类 + SLF4J 日志），通过 `@Cacheable` 实现高频接口缓存加速。修复了 `AnalysisServiceImpl` 双实现冲突，合并了缠论 Python 桥接调用。

---

### 2.5 `ai-service/` — AI 智能服务层 (FastAPI + Python) — ✅ 已完工

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
    ├── services/                       # ★ 核心业务服务
    │   ├── __init__.py
    │   ├── dialogue_service.py         #   对话服务（构建上下文 → 调用 AI → 返回回复）
    │   ├── multi_agent_service.py      #   多智能体深度分析（编排 7 Agent 流水线）
    │   └── memory_service.py           #   记忆服务（历史决策保存 + 自动反思对比）
    │
    ├── models/                         # ★ AI 模型客户端
    │   ├── __init__.py
    │   ├── model_registry.py           #   模型注册中心（管理多模型接入）
    │   ├── deepseek_client.py          #   DeepSeek API 客户端（HTTPS 调用）
    │   └── simulation.py               #   模拟回复引擎（无 API Key 时的降级策略）
    │
    └── utils/
        └── __init__.py
```

**角色定位**：系统的"智囊大脑" — ✅ 已完工。基于 FastAPI 构建的 AI 微服务，采用多智能体架构（7 个专业化 Agent 顺序执行），支持 DeepSeek API 实时分析 和 无 Key 模拟模式 两种工作方式，具备自动降级能力。通过 httpx 异步并行调用后端 3 个 API 获取实时数据上下文。

---

### 2.6 `frontend/` — 前端展示层 (Vue 3 + TypeScript) — ✅ 已完工

> **状态变更**: V2.0 — 完成代码重构：删除遗留 `api/stock.ts` 和 `KLineChart.vue`；新增 `useIndicatorParams` 组合函数；所有 `any` 类型替换为具体接口引用；Mock 数据全部替换为真实 API 调用。

```
frontend/
├── package.json                        # npm 项目配置
├── vite.config.ts                      # Vite 构建配置 + 开发代理（/api → localhost:8082）
├── tsconfig.json                       # TypeScript 编译配置
├── index.html                          # 入口 HTML
│
└── src/
    ├── main.ts                         # 应用入口（挂载 Vue、Pinia、Router、ElementPlus）
    ├── App.vue                         # 根组件
    │
    ├── api/                            # ★ API 封装层（Axios 实例 + 各模块 API）
    │   ├── request.ts                  #   Axios 实例（baseURL=/api, 15s 超时, JWT 拦截器, 401跳转）
    │   ├── types.ts                    #   API 层通用类型（分页Result、查询参数）
    │   ├── market.ts                   #   行情层 API（列表/详情/K线/搜索/行业/板块K线）
    │   ├── analysis.ts                 #   分析模块 API
    │   ├── signal.ts                   #   信号模块 API（题材/龙虎榜/北向/解禁/资金流向/行业对比）
    │   ├── info.ts                     #   [新增] 资讯模块 API（研报/新闻/公告/一致预期）
    │   ├── user.ts                     #   用户模块 API
    │   ├── watchlist.ts                #   自选模块 API
    │   ├── ai.ts                       #   AI 对话模块 API
    │   └── index.ts                    #   指数模块 API
    │
    ├── assets/                         # 静态资源
    │   ├── icons/                      #   图标库
    │   ├── images/                     #   图片资源
    │   └── styles/                     #   全局样式
    │
    ├── components/                     # ★ 可复用组件（9 个）
    │   ├── common/                     #   通用组件
    │   │   ├── AppHeader.vue           #     顶栏导航（含信号层下拉菜单 + 架构入口）
    │   │   ├── AppLayout.vue           #     页面布局框架
    │   │   └── AlertBell.vue           #     消息通知铃铛
    │   ├── chart/                      #   图表组件
    │   │   └── TreemapChart.vue        #     板块云图（ECharts 矩形树图）
    │   ├── ai/                         #   AI 相关组件
    │   │   ├── AiChatPanel.vue         #     AI 对话面板
    │   │   └── AiSignalSummary.vue     #     AI 信号摘要
    │   └── layer/                      #   [新增] 层架构详情组件
    │       ├── LayerStatusBadge.vue    #     层状态徽章（已完成/开发中/阻塞/待开始）
    │       ├── LayerSectionCard.vue    #     层卡片（完成度进度条 + 统计概要）
    │       └── LayerDetailPanel.vue    #     层详情面板（模块列表/技术栈/待解决项）
    │
    ├── views/                          # ★ 页面视图（19 个路由页面）
    │   ├── LoginView.vue               #   登录/注册
    │   ├── HomeView.vue                #   首页大盘（指数轮播、板块云图、信号卡片、热门股票）
    │   ├── StockListView.vue           #   股票列表（搜索、行业筛选、排序、分页）
    │   ├── StockDetailView.vue         #   个股详情（K线、技术指标、缠论、信号Tab、AI分析）
    │   ├── IndexDetailView.vue         #   指数详情
    │   ├── PortfolioView.vue           #   [V2.0 改进] 持仓管理（localStorage 持久化）
    │   ├── PortfolioView.vue           #   [V2.0 改进] 持仓管理（localStorage 持久化）
    │   ├── WatchlistView.vue           #   自选列表
    │   ├── ChatView.vue                #   AI 智能对话
    │   ├── NewsView.vue                #   [新增] 实时资讯
    │   ├── HotReasonView.vue           #   题材热点
    │   ├── DragonTigerView.vue         #   龙虎榜
    │   ├── NorthboundView.vue          #   北向资金
    │   ├── LockupView.vue              #   限售解禁
    │   ├── IndustryCompareView.vue     #   行业对比
    │   ├── FundFlowView.vue            #   [V2.0 改进] 资金流向（真实 API 替代 Mock）
    │   └── LayerDetailView.vue         #   [新增] 系统架构详情（L1~L6 全层展示）
    │
    ├── router/
    │   └── index.ts                    # Vue Router 路由配置（18 条路由 + 登录守卫）
    │
    ├── stores/                         # ★ Pinia 状态管理（3 个）
    │   ├── user.ts                     #   用户状态（登录/登出、Token 管理）
    │   ├── stock.ts                    #   行情状态（列表缓存、筛选条件、竞态控制）
    │   └── watchlist.ts                #   [新增] 自选状态（CRUD + 乐观更新）
    │
    ├── composables/                    # ★ [V2.0 新增] 组合函数
    │   ├── useTechnicalChart.ts        #   K 线图 ECharts 渲染（MA/BOLL/MACD/KDJ/RSI/缠论）
    │   └── useIndicatorParams.ts       #   [V2.0 新增] 指标参数管理（消除 StockDetail/SectorDetail 重复）
    │
    ├── styles/                         # 样式定义
    │   ├── variables.scss              #   SCSS 变量（颜色、字体、间距）
    │   └── global.scss                 #   全局样式
    │
    ├── types/                          # TypeScript 类型定义（50+ 接口）
    │   └── index.ts                    #   全局类型（Stock, Fund, Kline, Chanlun 等）
    │
    ├── utils/                          # 工具函数
    │   ├── format.ts                   #   格式化工具（价格、成交量、涨跌幅、日期）
    │   └── indicators.ts               #   前端指标计算（MA/BOLL/MACD/KDJ/RSI）
    │
    ├── i18n/                           # 国际化（预留）
    │   └── index.ts
    │
    └── __tests__/                      # 前端单元测试（15 个用例）
        ├── env.d.ts
        ├── setup.ts
        ├── api/request.test.ts          # 2 用例
        └── stores/
            ├── stock.test.ts            # 7 用例
            └── user.test.ts             # 6 用例
```

**角色定位**：用户交互界面 — ✅ 已完工。基于 Vue 3 + TypeScript + Pinia 构建的单页应用（SPA），通过 ECharts 实现丰富的金融数据可视化（K 线图、板块云图、资金流向图等），Element Plus 提供 UI 组件库。覆盖股票浏览、基金查询、技术分析、AI 对话、信号监控等 18 个功能页面，支持 JWT Token 自动注入与 401 自动跳转。V2.0 重构移除了全部 Mock 数据和 `any` 类型，新增 `useIndicatorParams` 组合函数消除视图间重复逻辑，新增板块 K 线聚合 API 调用。

---

### 2.7 `docker/` — 容器化部署配置

```
docker/
├── .env.dev                            # 开发环境变量
├── docker-compose.yml                  # ★ L2 大数据层编排（10 个容器）
├── docker-compose.collector.yml        # ★ [新增] L1 采集层编排（3 个容器）
├── docker-compose.prod.yml             # 生产环境覆盖配置（资源限制 + 安全加固）
├── docker-compose.bridge.yml           # [新增] 跨层网络桥接
├── docker-compose.dev.yml              # 开发环境覆盖配置
├── README.md                           # 部署说明
│
├── frontend/                           # 前端容器
│   ├── Dockerfile                      #   多阶段构建（Node → Nginx, <30MB）
│   ├── Dockerfile.dev                  #   开发构建（热重载）
│   └── nginx.conf
│
├── backend/                            # 后端容器
│   ├── Dockerfile                      #   多阶段构建（Maven → JRE, <200MB）
│   └── Dockerfile.dev                  #   开发构建
│
├── ai-service/                         # AI 服务容器
│   ├── Dockerfile                      #   多阶段构建（Python, <200MB）
│   └── Dockerfile.dev                  #   开发构建
│
├── collector/                          # [新增] 采集层容器
│   └── Dockerfile
│
├── mysql/
│   ├── init.sql                        #   ★ 初始化脚本（建库、建23张表、插种子数据）
│   └── migrate.sql                     #   数据库迁移脚本
│
├── hadoop/                             # Hadoop 配置
│   ├── core-site.xml
│   ├── hdfs-site.xml
│   ├── mapred-site.xml
│   └── yarn-site.xml
│
├── hive/
│   ├── conf/hive-site.xml
│   ├── entrypoint-wrapper.sh
│   └── lib/mysql-connector-j-8.0.33.jar
│
├── spark/
│   └── spark-defaults.conf
│
├── prometheus/                         # [新增] 监控配置
│   └── prometheus.yml
│
└── grafana/                            # [新增] 可视化配置
    ├── dashboards/
    └── datasources/
```

**容器清单（15 个容器，V2.0 更新 — 此前文档误标为 13 个）**：

| 层 | 服务 | 容器名 | CPU/Mem | 端口 | 健康检查 |
|:---|:-----|:-------|:--------|:----|:--------:|
| L1 | Zookeeper | `collector-zookeeper` | 0.5C/512M | 2181 | ✅ |
| L1 | Kafka | `collector-kafka` | 1C/1G | 9092/29092/39092 | ✅ |
| L1 | DataCollector | `data-collector` | 1C/1G | — | ✅ |
| L2 | HDFS NameNode | `namenode` | 2C/2G | 9870,9000 | ✅ |
| L2 | HDFS DataNode1 | `datanode1` | 2C/2G | 9864 | ✅ |
| L2 | HDFS DataNode2 | `datanode2` | 2C/2G | — | ✅ (V2.2 新增) |
| L2 | MySQL | `mysql` | 2C/2G | 3306 | ✅ |
| L2 | Redis | `redis` | 1C/256M | 6379 | ✅ |
| L2 | YARN ResourceManager | `resourcemanager` | 1C/1G | 8088 | ✅ |
| L2 | YARN NodeManager | `nodemanager1` | 2C/2G | — | — |
| L2 | Hive Server2 | `hive-server` | 2C/2G | 10000,10002 | ✅ |
| L2 | Spark Master | `spark-master` | 1C/1G | 8080,7077 | ✅ |
| L2 | Spark Worker | `spark-worker` | 2C/2G | 8081 | — |
| L4 | Backend | `backend` | 2C/2G | 8082 | ✅ |
| L5 | AI Service | `ai-service` | 1C/512M | 8000 | ✅ |
| L6 | Frontend | `frontend` | 0.5C/256M | 80 | ✅ |
| — | Prometheus | `prometheus` | — | 9090 | ✅ |
| — | Grafana | `grafana` | — | 3000 | ✅ |

**角色定位**：一键部署的"启动钥匙"。通过 Docker Compose 编排 18 个容器，实现全栈一键部署。提供生产/开发双模式 Dockerfile，Nginx 统一反向代理入口，Hadoop 全套配置文件。V2.0 新增采集层独立编排文件和双网络隔离架构（`collector-net` 与 `bigdata-net` 通过 Kafka 双网卡桥接）。

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

---

## 三、数据目录与日志

| 目录 | 说明 |
|:-----|:------|
| `data/` | Docker 持久化数据卷挂载点（MySQL 数据文件、HDFS 元数据等） |
| `logs/` | 运行日志目录 |
| `docs/` | 项目技术文档 |

---

## 四、六层架构

```
L6 前端展示层    frontend/   (Vue 3 + TypeScript + ECharts + Element Plus)          ✅
    ↑ Axios /api/ (经 Vite/Nginx 代理)
L5 AI 智能层     ai-service/ (FastAPI + 7 Agent 多智能体 + DeepSeek)                  ✅
    ↑ httpx 调用后端 API
L4 后端 API 层   backend/    (Spring Boot 3 + MyBatis-Plus + Redis + JWT)            ✅
    ↑ JDBC / Redis / Python 子进程调用
L3 算法分析层    analysis-algorithms/ (Python: AnalysisEngine + 技术指标 + 缠论 + 量化) ✅
    ↑ MySQL 连接池 / Redis 缓存
L2 大数据处理层  bigdata-processing/ (Hive SQL + Spark + MapReduce)                  ✅
    ↑ HDFS / MySQL
L1 数据采集层    data-collector/ (Python: 6数据源 + 适配器 + 管道 + 存储)              ✅
```

**数据流向**：采集层(L1) → 原始数据(CSV/JSON+HDFS+Kafka) → 大数据处理层(L2) → 预计算结果 → 算法分析层(L3) → 后端 API(L4) → 前端(L6) / AI 服务(L5)

---

## 五、变更记录

| 版本 | 日期 | 变更内容 |
|:-----|:-----|:---------|
| V1.0 | 2026-05-16 | 初始版本 |
| V1.1 | 2026-05-18 | L1/L2 标记完工，L3 标记为焦点 |
| **V2.0** | **2026-05-19** | **全线重构完毕 — 详见变更摘要** |
| | | • L3: 新增 `engine/` 和 `data/` 目录，AnalysisEngine 全流程编排 |
| | | • L4: 新增 `GlobalExceptionHandler`；修复 AnalysisService 双实现冲突；修正 Spring Boot 版本为 3.x；新增 8 个 Info* 实体/Service；新增板块 K 线聚合 SQL；废弃 StockController |
| | | • L6: 新增 `composables/useIndicatorParams.ts`；删除 `api/stock.ts` 和 `KLineChart.vue`；全部 `any` 替换为具体类型；Mock 数据全部替换为真实 API |
| | | • 数据表: 16 → 23 张（新增 7 张资讯层表） |
| | | • 容器: 13 → 18 个（新增采集层 ZK/Kafka/Collector + 监控 Prometheus/Grafana） |
| **V2.1** | **2026-05-20** | **关键缺陷修复与优化 + 测试覆盖增强** |
| | | • L2: `IndustryStatsMR.java` 重构 — 新增 DistributedCache 动态加载行业映射，保留硬编码回退，标准化股票代码补齐 |
| | | • L2: 新增 `export_industry_mapping.py` 脚本（MySQL/Hive → HDFS CSV） |
| | | • L4: `StockController.java` 增强废弃提示 — 所有响应添加 `X-API-Deprecated` + `X-API-Migration` 头 |
| | | • 测试: 新增 `IndustryStatsMRTest.java`（7 用例），增强 `StockControllerTest.java`（10 用例） |
| | | • **测试覆盖**: 新增 `MarketControllerTest`(15) + `FundControllerTest`(10) + `SignalDataControllerTest`(16) + `test_edge_cases.py`(18) + 前端测试 21 用例 → 总计 **120+ 测试用例** |
| | | • **E2E 测试**: 新增 `scripts/test_e2e_pipeline.py`（22 用例，模拟 L1→L6 全链路数据流） |
| | | • **ORC 迁移**: `migrate_hive_to_orc.py` 增强 — 日志/检查点续传/数据校验/自动建表 |
| | | • **前端类型**: 统一 `api/types.ts` ↔ `types/index.ts`，消除重复定义 |
| | | • **L6 架构页面**: 新增 `LayerDetailView.vue` + 3 个 layer 组件，展示 L1~L6 完整架构详情；导航栏新增"架构"入口 |
