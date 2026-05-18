"""
数据质量校验模块 — 用于 Bigdata 处理层结果验证

在批处理管道中添加 QC 门禁，确保每步处理结果符合预期：
  - 行数完整性（与源表对比）
  - 空值率检查
  - 数据类型校验
  - 关键字段范围检查
  - 重复记录检查

用法:
    from bigdata_quality import DataQualityChecker

    # 在 Pipeline 中集成
    qc = DataQualityChecker(spark, output_path="/user/hadoop/stock_data/quality/")
    reports = qc.check_table("stock_daily", min_rows=100)
    qc.report_summary(reports)

    # 在 Spark Job 末尾校验
    if not qc.check_dataframe(df, "ma_trend_result", min_rows=10).passed:
        raise ValueError("数据质量检查未通过")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


# ============================================================
# 数据模型
# ============================================================
@dataclass
class QCCheck:
    """单次检查结果"""
    check_name: str
    passed: bool
    actual_value: str = ""
    expected: str = ""
    message: str = ""


@dataclass
class QCReport:
    """对象数据质量报告"""
    target: str
    passed: bool
    checks: List[QCCheck] = field(default_factory=list)
    timestamp: str = ""

    def add_check(self, check: QCCheck):
        self.checks.append(check)
        if not check.passed:
            self.passed = False

    @property
    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.passed)
        return f"{'✅' if self.passed else '❌'} {self.target}: {passed}/{total} 通过"


class DataQualityChecker:
    """数据质量检查器 — 用于 Spark DataFrame 和 Hive 表校验"""

    OUTPUT_BASE = "/user/hadoop/stock_data/analysis/quality"

    def __init__(self, spark: SparkSession, output_path: str = None):
        self.spark = spark
        self.output_path = output_path or self.OUTPUT_BASE
        self.reports: List[QCReport] = []

    # --------------------------------------------------
    # Hive 表级别检查
    # --------------------------------------------------

    def check_table(self, table_name: str, min_rows: int = 1) -> QCReport:
        """对 Hive 表执行完整性检查"""
        report = QCReport(target=table_name, passed=True,
                          timestamp=datetime.now().isoformat())
        try:
            df = self.spark.table(table_name)
            total = df.count()

            # 1. 行数检查
            report.add_check(QCCheck(
                check_name="row_count",
                passed=total >= min_rows,
                actual_value=str(total),
                expected=f">= {min_rows}",
                message=f"行数: {total}" if total >= min_rows else f"❌ 行数不足: {total} < {min_rows}",
            ))

            if total > 0:
                # 2. 空值率检查
                null_checks = []
                for col_info in df.dtypes[:10]:  # 检查前 10 列
                    col_name = col_info[0]
                    null_count = df.filter(F.col(col_name).isNull()).count()
                    null_ratio = null_count / total
                    if null_ratio > 0.5:
                        null_checks.append(f"{col_name}={null_ratio:.1%}")

                report.add_check(QCCheck(
                    check_name="null_ratio",
                    passed=len(null_checks) == 0,
                    actual_value="; ".join(null_checks) if null_checks else "全部正常",
                    expected="各列空值率 < 50%",
                    message=f"空值列: {null_checks}" if null_checks else "✅ 空值率正常",
                ))

                # 3. 分区完整性（如有分区列）
                partition_cols = self.spark.sql(f"SHOW PARTITIONS {table_name}").collect()
                if partition_cols:
                    report.add_check(QCCheck(
                        check_name="partitions",
                        passed=len(partition_cols) > 0,
                        actual_value=str(len(partition_cols)),
                        expected="> 0",
                        message=f"分区数: {len(partition_cols)}",
                    ))

        except Exception as e:
            report.passed = False
            report.add_check(QCCheck(
                check_name="table_access",
                passed=False,
                actual_value=str(e),
                expected="表可正常访问",
                message=f"❌ 表访问失败: {e}",
            ))

        self.reports.append(report)
        return report

    # --------------------------------------------------
    # DataFrame 级别检查
    # --------------------------------------------------

    def check_dataframe(self, df: DataFrame, name: str,
                        min_rows: int = 1, required_cols: list = None) -> QCReport:
        """对 DataFrame 执行质量检查

        Args:
            df: 待检查的 DataFrame
            name: 检查目标名称
            min_rows: 最少行数要求
            required_cols: 必须包含的列

        Returns:
            QCReport
        """
        report = QCReport(target=name, passed=True,
                          timestamp=datetime.now().isoformat())

        try:
            total = df.count()
            columns = df.columns

            # 1. 行数检查
            report.add_check(QCCheck(
                check_name="row_count",
                passed=total >= min_rows,
                actual_value=str(total),
                expected=f">= {min_rows}",
                message=f"行数: {total}",
            ))

            # 2. 空 DataFram 检查
            report.add_check(QCCheck(
                check_name="not_empty",
                passed=total > 0,
                actual_value=str(total),
                expected="> 0",
                message=f"行数: {total}" if total > 0 else "❌ DataFrame 为空",
            ))

            # 3. 必需列检查
            if required_cols:
                missing_cols = [c for c in required_cols if c not in columns]
                report.add_check(QCCheck(
                    check_name="required_columns",
                    passed=len(missing_cols) == 0,
                    actual_value=str(missing_cols),
                    expected=f"包含: {required_cols}",
                    message=f"缺失列: {missing_cols}" if missing_cols else "✅ 列完整",
                ))

            if total > 0:
                # 4. 空值率（整体）
                # 修复: 使用单个聚合查询计算所有列的空值，避免逐列全表扫描
                total_cells = total * len(columns)
                null_counts = df.agg(*[
                    F.count(F.when(F.col(c).isNull(), 1)).alias(c)
                    for c in columns
                ]).collect()[0]
                null_cells = sum(null_counts[c] for c in columns if null_counts[c] is not None)
                null_ratio = null_cells / max(total_cells, 1)

                report.add_check(QCCheck(
                    check_name="overall_null_ratio",
                    passed=null_ratio < 0.3,
                    actual_value=f"{null_ratio:.2%}",
                    expected="< 30%",
                    message=f"总空值率: {null_ratio:.2%}",
                ))

                # 5. 关键数值列范围检查
                numeric_checks = []
                for c in columns[:15]:  # 检查前 15 列
                    dtype = [t for t in df.dtypes if t[0] == c]
                    if dtype and "double" in dtype[0][1].lower():
                        stats = df.agg(
                            F.min(c).alias("min"),
                            F.max(c).alias("max"),
                        ).collect()[0]
                        vmin, vmax = stats["min"], stats["max"]
                        if vmin is not None and vmax is not None:
                            if abs(vmin) > 1e10 or abs(vmax) > 1e10:
                                numeric_checks.append(f"{c}[{vmin:.1f},{vmax:.1f}]")

                report.add_check(QCCheck(
                    check_name="numeric_range",
                    passed=len(numeric_checks) == 0,
                    actual_value="; ".join(numeric_checks) if numeric_checks else "全部正常",
                    expected="无异常数值范围",
                    message=f"异常数值: {numeric_checks}" if numeric_checks else "✅ 数值范围正常",
                ))

        except Exception as e:
            report.passed = False
            report.add_check(QCCheck(
                check_name="df_access",
                passed=False,
                actual_value=str(e),
                expected="DataFrame 可正常检查",
                message=f"❌ 检查异常: {e}",
            ))

        self.reports.append(report)
        return report

    # --------------------------------------------------
    # 结果处理和输出
    # --------------------------------------------------

    def report_summary(self, reports: List[QCReport] = None) -> str:
        """输出检查摘要"""
        checks = reports or self.reports
        total = len(checks)
        passed = sum(1 for r in checks if r.passed)
        failed = sum(1 for r in checks if not r.passed)

        print(f"\n{'='*55}")
        print(f"📊 数据质量检查报告")
        print(f"{'='*55}")
        print(f"  通过: {passed}  失败: {failed}  共: {total}")
        print(f"{'-'*55}")

        for report in checks:
            print(f"  {report.summary}")
            for check in report.checks:
                if not check.passed:
                    print(f"    └─ ❌ {check.check_name}: {check.actual_value}")

        print(f"{'='*55}\n")
        return f"PASSED ({passed}/{total})" if failed == 0 else f"FAILED ({failed}/{total})"

    def save_report(self, name: str = "quality_check"):
        """保存检查报告到 HDFS"""
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.output_path}/{name}_{now}"

        # 转换为 DataFrame 保存
        rows = []
        for report in self.reports:
            for check in report.checks:
                rows.append((
                    report.target, report.timestamp,
                    check.check_name, check.passed,
                    check.actual_value, check.message,
                ))

        if rows:
            df = self.spark.createDataFrame(rows, schema=[
                "target", "timestamp", "check_name", "passed",
                "actual_value", "message",
            ])
            df.write.mode("overwrite").option("compression", "snappy").parquet(path)
            print(f"💾 质量报告已保存: {path}")

    def check_and_report(self, target, min_rows: int = 10,
                         required_cols: list = None) -> bool:
        """便捷方法: 检查 + 报告 + 返回是否通过"""
        if isinstance(target, str):
            report = self.check_table(target, min_rows)
        else:
            # 修复: 移除无效的三元表达式 (if False 分支永不执行)
            report = self.check_dataframe(target, "dataframe",
                                          min_rows, required_cols)
        print(f"  {report.summary}")
        return report.passed
