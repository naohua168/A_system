-- ============================================================
-- Hive DDL: 批处理检查点与错误恢复表
-- 用于记录批处理作业的执行状态，支持断点续跑和错误回溯
-- ============================================================

USE stock_analysis;

-- ============================================================
-- 1. 批处理检查点表
-- 记录每个作业的每次运行状态
-- status: started → completed / failed
-- ============================================================
DROP TABLE IF EXISTS batch_checkpoint;

CREATE TABLE batch_checkpoint (
    job_name       STRING  COMMENT '作业名称 (e.g. daily_pipeline)',
    batch_id       STRING  COMMENT '批次标识 (e.g. 20260513_001)',
    status         STRING  COMMENT '运行状态 (started/completed/failed)',
    mode           STRING  COMMENT '运行模式 (daily/incremental/rebuild)',
    started_at     STRING  COMMENT '开始时间 YYYY-MM-DD HH:MM:SS',
    completed_at   STRING  COMMENT '完成时间 YYYY-MM-DD HH:MM:SS',
    error_message  STRING  COMMENT '错误信息 (仅failed时非空)',
    record_count   BIGINT  COMMENT '处理记录数'
)
COMMENT '批处理检查点表 - 记录作业运行状态'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/system/checkpoint/'
TBLPROPERTIES ('skip.header.line.count' = '1');

-- ============================================================
-- 2. 批处理错误日志表
-- 记录作业执行过程中各步骤的详细错误
-- 支持错误回溯和重试决策
-- ============================================================
DROP TABLE IF EXISTS batch_error_log;

CREATE TABLE batch_error_log (
    job_name          STRING  COMMENT '作业名称',
    batch_id          STRING  COMMENT '批次标识',
    error_step        STRING  COMMENT '出错步骤 (hive_dml/spark_batch/mysql_sync)',
    error_message     STRING  COMMENT '详细错误信息',
    error_code        STRING  COMMENT '错误编码',
    raw_data_sample   STRING  COMMENT '导致错误的原始数据样例 (前1024字符)',
    occurred_at       STRING  COMMENT '错误发生时间'
)
COMMENT '批处理错误日志表 - 用于错误诊断和恢复'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '\"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/hadoop/stock_data/system/error_log/'
TBLPROPERTIES ('skip.header.line.count' = '1');
