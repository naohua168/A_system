# MapReduce 模块废弃说明

> 废弃日期: 2026-05-20 | 过渡期: 3 个月（至 2026-08-20）

## 原因

MapReduce 与 Spark Batch 功能完全重叠，统一到 Spark 可简化维护。

## Spark 对应实现

| MapReduce 作业 | Spark 等价实现 | 状态 |
|:---------------|:---------------|:----:|
| IndustryStatsMR | `spark/batch/sector_ranking.py` | ✅ 已完成 |
| MonthlyReturnMR | `spark/batch/monthly_return.py` | ✅ 已完成 |
| TechnicalIndicatorMR | `spark/batch/precompute_indicators.py` | ✅ 已完成 |
| VolumeAnalysis | `spark/batch/ma_trend.py` (含成交量) | ✅ 已完成 |

## 迁移时间线

- **2026-08-20 前**: MR 代码保留，仅标记废弃
- **2026-08-20 后**: 删除 `mapreduce/` 目录

## 验证

运行 `pyspark` 作业确认输出与 MR 一致：
```bash
# Spark 批处理验证
python spark/batch/run_batch_pipeline.py --mode verify
```
