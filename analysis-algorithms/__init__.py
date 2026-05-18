"""
analysis-algorithms — 分析算法库（优化版）

适配新数据架构:
  - 数据来源: 存储层 MySQL（由 data-loader → Kafka → Spark → MySQL 管道填充）
  - 分析结果: 写回 MySQL + Redis 缓存（供后端 API 实时读取）
  - 技术指标: 优先使用 Spark 预计算结果，回退到本地 Pandas 计算
  - 缠论/量化: 本地计算（算法复杂，不适合 Spark 实现）

模块组织:
  technical/      技术指标（MA / MACD / RSI / KDJ / 布林带）
  chanlun/        缠论六步递归分解
  quantitative/   量化策略回测
  utils/          数据加载工具
  analysis_orchestrator.py  统一分析引擎（对外唯一入口）

使用方式:
  from analysis_orchestrator import analyze, rank

  # 单股全量分析
  result = analyze("000001")

  # 股票排名
  top20 = rank("change_pct", 20)
"""

from . import technical
from . import chanlun
from . import quantitative
from .analysis_orchestrator import AnalysisEngine, analyze, rank
