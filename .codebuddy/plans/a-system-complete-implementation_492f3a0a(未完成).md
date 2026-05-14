---
name: a-system-complete-implementation
overview: 基于数据采集层全量数据驱动，补全 bigdata-processing 缺失17个文件和 ai-service 缺失12个文件，实现从"代码写完"到"系统可运行"的完整跨越
todos:
  - id: full-market-collect
    content: 创建全市场采集脚本 full_market_collect.py（断点续采+分批+延时）
    status: pending
  - id: run-collect-sync
    content: 运行全市场采集并同步MySQL，验证数据完整性
    status: pending
    dependencies:
      - full-market-collect
  - id: spark-batch-core
    content: 创建Spark批处理核心3个作业：yearly_return.py + ma_trend.py + sector_ranking.py
    status: pending
    dependencies:
      - run-collect-sync
  - id: spark-batch-extend
    content: 创建Spark批处理扩展4个作业：monthly_return + correlation + filter_stocks + trend_judge
    status: pending
    dependencies:
      - spark-batch-core
  - id: batch-pipeline
    content: 创建批处理管道调度器 run_batch_pipeline.py（3种模式+检查点）
    status: pending
    dependencies:
      - spark-batch-extend
  - id: hive-ddl-dml
    content: 创建Hive DDL(2个) + DML(4个)扩展文件
    status: pending
    dependencies:
      - run-collect-sync
  - id: mapreduce-extend
    content: 创建MapReduce 3个扩展作业（MonthlyReturn + IndustryStats + TechnicalIndicator）
    status: pending
    dependencies:
      - run-collect-sync
  - id: precomputed-table
    content: 创建预计算结果表DDL + 后端Entity/Mapper + AnalysisServiceImpl改造
    status: pending
    dependencies:
      - batch-pipeline
  - id: agent-base-core
    content: 创建多智能体基类 + 核心Agent（base_agent + fundamentals + technical + sentiment）
    status: pending
  - id: agent-extend
    content: 创建扩展Agent（news + researcher_team + trader + risk_manager）
    status: pending
    dependencies:
      - agent-base-core
  - id: ai-infra
    content: 创建统一模型目录(model_registry) + 模拟降级(simulation) + 编排服务(multi_agent_service) + 记忆服务(memory_service)
    status: pending
    dependencies:
      - agent-base-core
  - id: e2e-verify
    content: 端到端验证：采集→MySQL→API→前端→AI多智能体全链路跑通
    status: pending
    dependencies:
      - precomputed-table
      - ai-infra
---

## 产品概述

完整补全 A_system 股票智能分析系统的三大缺失层：数据采集层（全市场数据初始化）、大数据处理层（批处理管道+离线计算）、AI服务层（多智能体架构），使项目从"代码写完但没跑起来"变为"端到端可运行的完整系统"。

## 核心功能

- 全市场数据采集初始化：扩展采集器支持全市场5000+股票，自动采集K线/实时行情/信号层数据，同步到MySQL
- 大数据批处理管道：7个Spark批处理作业替代后端Java内存计算，Hive DDL/DML扩展，MapReduce离线作业扩展，统一调度器
- AI多智能体架构：7个Agent角色（基本面/技术/情绪/新闻分析师 + 研究员辩论 + 交易员 + 风控），统一模型目录，持久化记忆+反思
- 全链路验证：采集→MySQL→后端API→前端页面完整跑通

## 技术栈

- 数据采集：Python 3.10+ / mootdx / akshare / requests
- 大数据层：PySpark 3.x / Hive SQL / MapReduce(Java 8) / HDFS
- AI服务：Python / FastAPI / httpx（已有DeepSeek客户端）
- 后端：Java 17 / Spring Boot 3 / MyBatis
- 前端：Vue 3 / TypeScript / ECharts / Element Plus

## 实现方案

### 一、数据采集层初始化（全市场）

**核心问题**：采集器代码100%完成，但`data/`目录完全为空，MySQL只有20只股票5天K线的种子数据。

**方案**：

1. 创建 `data-collector/scheduler/full_market_collect.py` — 全市场采集脚本

- 使用 akshare 获取全部A股代码列表（~5000只）
- 分批采集K线（每批100只，避免触发反爬）
- 信号层数据全量采集（题材热点/北向资金/行业对比/龙虎榜）
- 实时行情批量采集
- 内置断点续采（记录已采集代码到 `data/raw/progress.json`）

2. 扩展 `run_collector.py` — 新增 `--full-market` 参数
3. 运行 `sync_to_mysql.py` — 同步所有CSV到MySQL 16张表

**性能考量**：全市场5000只K线采集约需2-3小时，采用分批+延时策略避免封IP。

### 二、大数据处理层补全（17个文件）

**架构**：

```
HDFS/Hive分区表 → Spark批处理(7个作业) → MySQL预计算结果表 → API O(1)查询
                → Hive DML多维分析 → 物化视图
                → MapReduce离线计算(3个作业) → HDFS结果
```

**2.1 Spark批处理作业** (`bigdata-processing/spark/batch/`)
7个作业替代后端Java内存计算：

- `yearly_return.py`：ROW_NUMBER窗口函数取每年首末行，一次扫描全市场年收益率
- `monthly_return.py`：GROUP BY stock_code+月份 + FIRST_VALUE/LAST_VALUE
- `ma_trend.py`：AVG(close) OVER滑动窗口一次算出MA5/10/20/60
- `correlation.py`：Spark corr()函数批量计算股票相关系数
- `sector_ranking.py`：每日JOIN stock_basic计算行业聚合排行
- `filter_stocks.py`：预计算所有筛选组合结果
- `trend_judge.py`：NTILE(2)分区后均值比较判断趋势

**2.2 批处理管道调度器** (`bigdata-processing/batch/run_batch_pipeline.py`)

- 三种模式：daily(全量)/incremental(增量)/rebuild(全量重算)
- 检查点恢复支持
- 步骤：Hive MSCK REPAIR → Hive DML → Spark批处理(7个作业) → sync_to_mysql

**2.3 Hive扩展**

- DDL：`precomputed_results.sql`（3张预计算结果表）、`recovery_checkpoint.sql`
- DML：`analysis_correlation.sql`、`analysis_year_comparison.sql`、`analysis_technical.sql`、`analysis_signal_fusion.sql`

**2.4 MapReduce扩展** (`mapreduce/src/main/java/com/stock/mr/`)

- `MonthlyReturnMR.java`：批量月收益率
- `IndustryStatsMR.java`：行业多维度统计
- `TechnicalIndicatorMR.java`：全市场技术指标

**2.5 预计算结果表 + 后端改造**

- MySQL新增3张表：precomputed_return / precomputed_ma / precomputed_sector
- 后端AnalysisServiceImpl：优先查预计算表，查不到降级到原始Java计算

### 三、AI服务层补全（12个文件）

**架构**：多智能体协作，借鉴TradingAgents项目

```
用户提问
  ├── 基本面分析师 — LLM解读PE/PB/ROE（调用后端API）
  ├── 技术分析师 — LLM解读缠论信号+MA/MACD（调用分析API）
  ├── 情绪分析师 — LLM解读题材归因+资金流向（调用信号层API）
  ├── 新闻分析师 — LLM解读最新新闻/研报
  ├── 研究员团队 — 看涨vs看跌多轮辩论
  ├── 交易员 — 综合报告→交易决策
  └── 风控经理 — 风险评估→批准/拒绝
```

**3.1 Agent模块** (`ai-service/app/agents/`)
7个Agent文件，每个继承BaseAgent基类，统一接口：

- `base_agent.py`：抽象基类（name/role/system_prompt/chat方法）
- `fundamentals_analyst.py`：调用`/api/stock/{code}`获取基本面数据
- `technical_analyst.py`：调用`/api/analysis/{code}/trend`获取技术分析
- `sentiment_analyst.py`：调用信号层API获取题材/资金数据
- `news_analyst.py`：调用新闻API获取资讯
- `researcher_team.py`：看涨vs看跌多轮辩论（2-3轮）
- `trader_agent.py`：综合所有Agent报告生成交易决策
- `risk_manager.py`：风险评估，批准/拒绝/调整交易提案

**3.2 统一模型目录** (`ai-service/app/models/`)

- `model_registry.py`：统一接口，支持DeepSeek/OpenAI/Claude/Qwen等，自动故障转移
- `simulation.py`：多智能体模拟降级（每个Agent角色至少2个模板，无API Key时可用）

**3.3 编排与记忆服务** (`ai-service/app/services/`)

- `multi_agent_service.py`：编排Agent调用顺序、超时、错误处理
- `memory_service.py`：决策日志持久化 + 自动反思（`~/.a_system/memory/`）

## 目录结构

```
project-root/
├── data-collector/
│   └── scheduler/
│       └── full_market_collect.py        # [NEW] 全市场采集脚本，断点续采
├── bigdata-processing/
│   ├── batch/
│   │   └── run_batch_pipeline.py         # [NEW] 批处理管道调度器
│   ├── spark/
│   │   └── batch/                        # [NEW] Spark批处理目录
│   │       ├── yearly_return.py          # [NEW] 年收益率批处理
│   │       ├── monthly_return.py         # [NEW] 月收益率批处理
│   │       ├── ma_trend.py               # [NEW] MA趋势批处理
│   │       ├── correlation.py            # [NEW] 相关系数批处理
│   │       ├── sector_ranking.py         # [NEW] 行业排行批处理
│   │       ├── filter_stocks.py          # [NEW] 股票筛选批处理
│   │       └── trend_judge.py            # [NEW] 趋势判断批处理
│   ├── hive/
│   │   ├── ddl/
│   │   │   ├── precomputed_results.sql   # [NEW] 预计算结果表DDL
│   │   │   └── recovery_checkpoint.sql   # [NEW] 检查点恢复DDL
│   │   └── dml/
│   │       ├── analysis_correlation.sql   # [NEW] 相关系数分析
│   │       ├── analysis_year_comparison.sql # [NEW] 多年同比分析
│   │       ├── analysis_technical.sql     # [NEW] 技术指标分析
│   │       └── analysis_signal_fusion.sql # [NEW] 信号融合分析
│   └── mapreduce/src/main/java/com/stock/mr/
│       ├── MonthlyReturnMR.java          # [NEW] 月收益率MR
│       ├── IndustryStatsMR.java          # [NEW] 行业统计MR
│       └── TechnicalIndicatorMR.java      # [NEW] 技术指标MR
├── backend/src/main/java/com/stock/
│   ├── entity/
│   │   └── PrecomputedResult.java        # [NEW] 预计算结果Entity
│   ├── mapper/
│   │   └── PrecomputedResultMapper.java  # [NEW] 预计算Mapper
│   └── service/impl/
│       └── AnalysisServiceImpl.java      # [MODIFY] 优先查预计算表
├── ai-service/app/
│   ├── agents/                           # [NEW] 多智能体目录
│   │   ├── base_agent.py                 # [NEW] Agent抽象基类
│   │   ├── fundamentals_analyst.py       # [NEW] 基本面分析师
│   │   ├── technical_analyst.py          # [NEW] 技术分析师
│   │   ├── sentiment_analyst.py          # [NEW] 情绪分析师
│   │   ├── news_analyst.py               # [NEW] 新闻分析师
│   │   ├── researcher_team.py            # [NEW] 研究员辩论
│   │   ├── trader_agent.py               # [NEW] 交易员
│   │   └── risk_manager.py              # [NEW] 风控经理
│   ├── models/
│   │   ├── model_registry.py             # [NEW] 统一模型目录
│   │   └── simulation.py                 # [NEW] 多智能体模拟降级
│   └── services/
│       ├── multi_agent_service.py        # [NEW] 多智能体编排引擎
│       └── memory_service.py             # [NEW] 持久化记忆+反思
```

## Agent Extensions

### Skill

- **All-Market Financial Data Hub**
- Purpose: 用于全市场股票代码获取和金融数据补充查询，替代/补充mootdx和akshare采集
- Expected outcome: 获取全市场A股代码列表（~5000只），补充实时行情和基本面数据

### SubAgent

- **code-explorer**
- Purpose: 在实现每个模块前快速定位相关代码、验证接口签名、确认现有模式
- Expected outcome: 确保新代码与现有架构一致，避免重复造轮子