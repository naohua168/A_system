# MapReduce 模块废弃说明

> 废弃日期: 2026-05-20 | 实际删除: 2026-05-20

## 原因

MapReduce 与 Spark Batch 功能完全重叠，统一到 Spark 可简化维护。

## Spark 对应实现

| MapReduce 作业 | Spark 等价实现 | 状态 |
|:---------------|:---------------|:----:|
| IndustryStatsMR | `spark/batch/sector_ranking.py` | ✅ 已完成 |
| MonthlyReturnMR | `spark/batch/monthly_return.py` | ✅ 已完成 |
| TechnicalIndicatorMR | `spark/batch/precompute_indicators.py` | ✅ 已完成 |
| VolumeAnalysis | `spark/batch/ma_trend.py` (含成交量) | ✅ 已完成 |

## 清理记录

MapReduce 源码目录 (`bigdata-processing/mapreduce/`) 已于 2026-05-20 删除。
Spark 批处理已验证为等价替代。
