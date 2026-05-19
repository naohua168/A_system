"""
analysis-algorithms — 分析算法库 L3

新架构 — 三层解耦:
  data/      数据访问层（读 MySQL → 统一列名映射 → 降级策略）
  engine/    分析编排层（编排技术指标 + 缠论 + 量化 → 结果持久化）
  scheduler/ 批量调度层（全量/增量/单股三种运行模式）

算法模块（纯计算，无数据依赖）:
  technical/   技术指标（MA/MACD/KDJ/RSI/布林带）
  chanlun/     缠论六步递归分解（分型→笔→线段→中枢→买卖点）
  quantitative/量化策略回测（MA/动量/多因子 + 回测引擎）

与上下游的依赖关系:
  ← L2 (bigdata-processing): 读 MySQL precomputed_* 预计算结果
  ← L1 (data-collector):      读 MySQL stock_daily / stock / signal_* 表
  → L4 (backend):             写 MySQL analysis_result 表供后端 API 查询

使用方式:
  from engine import analyze, rank

  # 单股全量分析（结果自动写回 MySQL → 后端 API 可读）
  result = analyze("000001")

  # 股票排名
  top20 = rank("change_percent", 20)

CLI 批量运行:
  python -m scheduler.batch_runner --mode daily          # 全量
  python -m scheduler.batch_runner --mode incremental     # 增量
  python -m scheduler.batch_runner --mode single --code 000001  # 单股
"""

from engine import AnalysisEngine, get_engine, analyze, rank

__all__ = [
    "AnalysisEngine",
    "get_engine",
    "analyze",
    "rank",
]
