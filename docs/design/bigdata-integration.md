# 大数据集成方案：Lambda 架构 + 每日复盘大屏

> **版本**: v1.0  
> **日期**: 2026-06-03  
> **作者**: A_system 架构组  

---

## 一、概述

本项目采用 **Lambda 架构**（速度层 + 批处理层 + 服务层），在保持现有实时链路（Redis + WebSocket）的前提下，引入 Hadoop 生态组件存储全量历史数据并提供离线分析能力，最终通过**每日复盘大屏**呈现 Hive 分析结果。

### 核心目标

1. **Hadoop 盘后 18:00 更新一次**，盘中零写，不干扰实时性能
2. **HBase 为 Redis 兜底**，采集 API 挂掉时前端仍有数据
3. **每日 20:00 推送市场复盘**，所有数据来自 Hive ETL 分析
4. **非伪分布式**部署，6 个独立 Docker 容器模拟真实 Hadoop 集群
5. **前端所有数据在 HDFS 存全量版本**（K线/行情/信号/资讯）

---

## 二、整体架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         实时链路（盘中）                                    │
│                                                                          │
│  腾讯行情API ─→ CSV ─→ auto_seed(2min) ─→ Redis ─→ WS(15s) ─→ 前端页面   │
│                      （force_write）              （4主题广播）             │
│                                                                          │
│                              兜底链路（Redis miss 时）                      │
│                          前端请求 ─→ 后端查 Redis                          │
│                                        ├─ 命中 → 返回                     │
│                                        └─ miss → 查 HBase stock_fallback  │
│                                                 ├─ 查到 → 写回 Redis+返回  │
│                                                 └─ 未查到 → 返回空态       │
│                                                                          │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│                         批处理链路（盘后 18:00）                            │
│                                                                          │
│  15:00 收盘                                                            │
│      ↓                                                                   │
│  18:00 hdfs_upload.py → CSV → Parquet → HDFS /data/ods/                  │
│      ↓                                                                   │
│  Hive ETL: ODS → DWD(清洗) → DWS(聚合) → ADS(大屏结果)                   │
│      ↓                                                                   │
│  20:00 hdfs_to_redis.py → Redis（复盘数据，TTL=27h）                      │
│  20:00 hbase_sync.py → HBase stock_fallback（30天K线+最新价）             │
│                                                                          │
│  复盘后台: 前端读 Redis → 展示每日复盘大屏                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### 每日时间线

```
09:00        09:30                   15:00    18:00    20:00
  │            │                      │        │        │
  │ auto_seed  │ WS广播               │ 收盘    │Hive   │ 复盘
  │ 刷新Redis  │ 指数/信号/价格        │ HDFS    │ETL完  │ 推送
  │ (每2min)   │                      │ 数据落盘│成     │
```

---

## 三、Hadoop 集群部署（6 个独立容器，真实分布式）

| 组件 | 容器名 | 镜像 | 端口 |
|------|--------|------|------|
| **NameNode** | `namenode` | `bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8` | 9870(UI), 9000(RPC) |
| **DataNode 1** | `datanode1` | `bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8` | 9864 |
| **DataNode 2** | `datanode2` | `bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8` | 9864 |
| **Hive Metastore** | `hive-metastore` | `bde2020/hive:2.3.2-postgresql-metastore` | 9083 |
| **Hive Server2** | `hive-server` | `bde2020/hive:2.3.2` | 10000 |
| **HBase Master** | `hbase-master` | `harisekhon/hbase:2.2.6` | 16010(UI) |
| **HBase RegionServer** | `hbase-region` | `harisekhon/hbase:2.2.6` | 16030 |

所有容器加入 `bigdata-net` 网络，与现有 `redis`/`backend`/`mysql`/`data-collector` 容器互通。

> 这不是伪分布式。每个组件运行在独立容器、独立 JVM、独立端口，与生产环境多节点部署逻辑一致。

---

## 四、HDFS 存储设计（全量数据）

```
/data/stock/
├── ods/                                              ← 原始数据层
│   ├── kline_daily/dt=2026-06-03/      Parquet       ← 日K线（5000只×750日≈375万条）
│   ├── kline_1min/dt=2026-06-03/       Parquet       ← 1分钟K线（近90天≈3亿条）
│   ├── kline_5min/dt=2026-06-03/       Parquet       ← 5分钟K线
│   ├── kline_15min/dt=2026-06-03/      Parquet       ← 15分钟K线
│   ├── kline_30min/dt=2026-06-03/      Parquet       ← 30分钟K线
│   ├── kline_60min/dt=2026-06-03/      Parquet       ← 60分钟K线
│   ├── kline_weekly/                   Parquet       ← 周K线（从日K聚合，无日期分区）
│   ├── kline_monthly/                  Parquet       ← 月K线（从日K聚合，无日期分区）
│   ├── market_snapshot/dt=2026-06-03/  Parquet       ← 当日收盘行情快照
│   ├── northbound/dt=2026-06-03/       Parquet       ← 北向资金
│   ├── dragon_tiger/dt=2026-06-03/     Parquet       ← 龙虎榜
│   ├── fund_flow/dt=2026-06-03/        Parquet       ← 资金流向
│   ├── industry_compare/dt=2026-06-03/ Parquet       ← 行业排行快照
│   ├── index_kline/dt=2026-06-03/      Parquet       ← 指数K线
│   └── news/dt=2026-06-03/             Parquet       ← 财经资讯
│
├── dwd/                                              ← 明细层（清洗后）
│   └── kline_daily_clean/dt=2026-06-03/             ← 去重/空值填充后日K线
│
├── dws/                                              ← 汇总层
│   ├── industry_rotation/              非分区        ← 行业轮动（5日Pivot）
│   ├── capital_summary/                非分区        ← 资金汇总TOP20
│   ├── technical_scan/                 非分区        ← 全市场技术扫描
│   ├── northbound_trend/               非分区        ← 北向资金趋势
│   └── market_overview/dt=2026-06-03/               ← 当日市场概览
│
└── ads/                                               ← 大屏数据层
    ├── top_stocks/                     非分区        ← 涨跌TOP/成交额TOP
    └── dragon_tiger_summary/           非分区        ← 龙虎榜汇总分析
```

### 数据量估算

| 层级 | 日增量 | 5年累计(压缩后) |
|------|--------|----------------|
| ODS 日K线 | ~6MB | ~3 GB |
| ODS 分钟K线 | ~20MB | ~10 GB |
| ODS 信号/快照 | ~1MB | ~0.5 GB |
| DWS 聚合结果 | ~50KB | ~25 MB |
| **HDFS 总计** | **~27MB/日** | **~14 GB** |

> 单节点 Hadoop 完全胜任，HDFS 默认 3 副本后约 42 GB，在毕设演示环境可配置为 2 副本。

---

## 五、Hive 数仓分层设计

### 5.1 外部表 DDL

#### ODS 层（数据格式：Parquet，压缩：Zstd）

```sql
-- 日K线原始数据
CREATE EXTERNAL TABLE ods_kline_daily (
    stock_code  STRING,
    trade_date  STRING,
    open_price  DOUBLE,
    high_price  DOUBLE,
    low_price   DOUBLE,
    close_price DOUBLE,
    volume      BIGINT,
    amount      DOUBLE,
    change_pct  DOUBLE,
    pre_close   DOUBLE,
    turnover_rate DOUBLE
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '/data/stock/ods/kline_daily';

-- 分钟K线
CREATE EXTERNAL TABLE ods_kline_1min (
    stock_code  STRING,
    trade_time  STRING,
    open_price  DOUBLE,
    high_price  DOUBLE,
    low_price   DOUBLE,
    close_price DOUBLE,
    volume      BIGINT,
    amount      DOUBLE
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '/data/stock/ods/kline_1min';

-- 当日收盘行情快照
CREATE EXTERNAL TABLE ods_market_snapshot (
    stock_code  STRING,
    stock_name  STRING,
    price       DOUBLE,
    change_pct  DOUBLE,
    turnover_pct DOUBLE,
    pe_ttm      DOUBLE,
    pb          DOUBLE,
    mcap_yi     DOUBLE
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '/data/stock/ods/market_snapshot';

-- 行业排行快照
CREATE EXTERNAL TABLE ods_industry_compare (
    industry_name STRING,
    change_pct    DOUBLE,
    stock_count   INT,
    total_amount  DOUBLE,
    up_count      INT,
    down_count    INT
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '/data/stock/ods/industry_compare';
```

#### DWS 层

```sql
-- 行业轮动（5日Pivot）
CREATE EXTERNAL TABLE dws_industry_rotation (
    industry_name STRING,
    d0_change     DOUBLE,
    d1_change     DOUBLE,
    d2_change     DOUBLE,
    d3_change     DOUBLE,
    d4_change     DOUBLE,
    avg_5d_change DOUBLE,
    total_inflow  DOUBLE
)
STORED AS PARQUET
LOCATION '/data/stock/dws/industry_rotation';

-- 全市场技术扫描
CREATE EXTERNAL TABLE dws_technical_scan (
    stock_code       STRING,
    stock_name       STRING,
    ma5              DOUBLE,
    ma20             DOUBLE,
    macd             DOUBLE,
    rsi              DOUBLE,
    kdj_k            DOUBLE,
    kdj_d            DOUBLE,
    golden_cross     BOOLEAN,
    death_cross      BOOLEAN,
    overbought       BOOLEAN,
    oversold         BOOLEAN
)
STORED AS PARQUET
LOCATION '/data/stock/dws/technical_scan';

-- 资金汇总
CREATE EXTERNAL TABLE dws_capital_summary (
    stock_code       STRING,
    stock_name       STRING,
    super_net_in     DOUBLE,
    large_net_in     DOUBLE,
    medium_net_in    DOUBLE,
    little_net_in    DOUBLE,
    main_net_in      DOUBLE
)
STORED AS PARQUET
LOCATION '/data/stock/dws/capital_summary';
```

### 5.2 核心 ETL SQL

```sql
-- 行业轮动：近5日各行业涨跌幅Pivot
INSERT OVERWRITE TABLE dws_industry_rotation
SELECT industry_name,
       MAX(CASE WHEN days_ago=0 THEN change_pct END) AS d0_change,
       MAX(CASE WHEN days_ago=1 THEN change_pct END) AS d1_change,
       MAX(CASE WHEN days_ago=2 THEN change_pct END) AS d2_change,
       MAX(CASE WHEN days_ago=3 THEN change_pct END) AS d3_change,
       MAX(CASE WHEN days_ago=4 THEN change_pct END) AS d4_change,
       AVG(change_pct) AS avg_5d_change,
       SUM(net_inflow) AS total_inflow
FROM (
    SELECT ic.industry_name, ic.change_pct,
           DATEDIFF('2026-06-03', ic.dt) AS days_ago,
           ic.stock_count * ic.change_pct AS net_inflow
    FROM ods_industry_compare ic
    WHERE ic.dt >= DATE_SUB('2026-06-03', 5)
) t
GROUP BY industry_name;

-- 技术扫描：全市场MA/MACD/RSI
INSERT OVERWRITE TABLE dws_technical_scan
SELECT k.stock_code, s.stock_name,
       AVG(k.close_price) OVER (PARTITION BY k.stock_code ORDER BY k.trade_date ROWS 4 PRECEDING) AS ma5,
       AVG(k.close_price) OVER (PARTITION BY k.stock_code ORDER BY k.trade_date ROWS 19 PRECEDING) AS ma20,
       -- MACD/RSI/KDJ计算（省略具体公式）
       -- ...
FROM ods_kline_daily k
JOIN ods_market_snapshot s ON k.stock_code = s.stock_code AND s.dt = '2026-06-03'
WHERE k.dt >= DATE_SUB('2026-06-03', 60);
```

---

## 六、HBase 兜底设计

### 6.1 表结构

```
表名: stock_fallback
列族: cf

RowKey 设计:
  [反转前4位][stock_code]
  例: 600519 → "0000600519"
      000001 → "1000000001"
      300750 → "0750300750"

数据内容:
  RowKey        cf:price        cf:changePct     cf:kline(JSON)
  ───────       ────────        ────────────     ──────────────────
  0000600519    "1900.00"       "1.23"           [{tradeDate,open,high,low,close,volume}, ...30条]
```

### 6.2 兜底流程

```
前端请求 → 后端查 Redis
         ├─ 命中 → 直接返回（~1ms）
         └─ 未命中 → 查 HBase stock_fallback
                     ├─ 查到 → 写回 Redis（TTL=36h）+ 返回（~50ms）
                     └─ 未查到 → 返回空态
```

### 6.3 日终同步（20:00）

```python
# hbase_sync.py 伪代码
from hdfs import InsecureClient
import happybase

hdfs = InsecureClient('http://namenode:9870')
hbase = happybase.Connection('hbase-master')

# 从 HDFS 读取今日数据
with hdfs.read('/data/stock/ods/market_snapshot/dt=2026-06-03/') as f:
    stocks = read_parquet(f)  # 5000只

# 从 HDFS 读取近30天K线
with hdfs.read('/data/stock/ods/kline_daily/') as f:
    klines = read_parquet_partitions(f, '2026-05-04', '2026-06-03')

# 写入 HBase
table = hbase.table('stock_fallback')
batch = table.batch()
for stock in stocks:
    rowkey = reverse_code(stock['stock_code'])
    kline_30d = [k for k in klines if k['stock_code'] == stock['stock_code']]
    batch.put(rowkey, {
        b'cf:price':     str(stock['price']),
        b'cf:changePct': str(stock['change_pct']),
        b'cf:kline':     json.dumps(kline_30d, ensure_ascii=False),
    })
batch.send()
```

---

## 七、每日复盘大屏设计

### 7.1 模块列表

| 模块 | 数据源（Redis Key） | 可视化组件 | Hive 来源表 |
|------|-------------------|-----------|------------|
| **市场温度** | `review:market_overview:{dt}` | 4 张大数字卡 + 涨跌比例条 | `dws_market_overview` |
| **行业轮动** | `review:industry_rotation:{dt}` | ECharts 热力图（x=5日, y=行业） | `dws_industry_rotation` |
| **资金流向TOP** | `review:capital_summary:{dt}` | 横向条形图（红入/绿出） | `dws_capital_summary` |
| **北向资金** | `review:northbound_trend:{dt}` | 双折线图（沪/深渠道） | `dws_northbound_trend` |
| **龙虎榜汇总** | `review:dragon_tiger:{dt}` | 卡片列表 + 净买入/卖 | `dws_dragon_tiger` |
| **技术扫描** | `review:technical_scan:{dt}` | 4 圆环进度图（金叉/死叉/超买/超卖） | `dws_technical_scan` |
| **明星/衰股** | `review:top_stocks:{dt}` | 红绿对比卡片 | `dws_top_stocks` |

### 7.2 页面布局

```
┌──────────────────────────────────────────────────────────────┐
│  █ 今日市场复盘 · 2026-06-03                   20:00 推送   │
├──────────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                         │
│ │ 涨   │ │ 跌   │ │ 涨停 │ │ 成交 │                         │
│ │ 2180 │ │ 1120 │ │  85  │ │ 1.2万亿│                       │
│ └──────┘ └──────┘ └──────┘ └──────┘                         │
├──────────────────────────────────────────────────────────────┤
│  行业轮动热力图（横向5日，纵向所有行业）                       │
├────────────────────────────┬─────────────────────────────────┤
│  资金流向TOP10             │  北向资金趋势                    │
│ ┌──────┐                   │ ┌──────┐                       │
│ │茅台+12亿│                │ │ 折线图│                       │
│ └──────┘                   │ └──────┘                       │
├────────────────────────────┴─────────────────────────────────┤
│  技术指标扫描                                                  │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐                                │
│  │金叉 │ │死叉 │ │超买 │ │超卖 │                                │
│  │125只│ │ 89只│ │342只│ │156只│                                │
│  └────┘ └────┘ └────┘ └────┘                                │
├──────────────────────────────────────────────────────────────┤
│ 今日明星                       今日衰股                        │
│ TOP1: 茅台 +5.2%              TOP1: 平安 -4.8%              │
│ TOP2: 宁德 +4.5%              TOP2: 招行 -3.2%              │
│ TOP3: 中免 +3.8%              TOP3: 万科 -2.9%              │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 日终调度脚本

```bash
#!/bin/bash
# daily_etl.sh — 每日 18:00 由 cron/task 触发

# 步骤1: CSV → HDFS Parquet
echo "[18:00] hdfs_upload starting..."
python /app/hdfs_upload.py --date $(date +%Y-%m-%d)

# 步骤2: Hive ETL
echo "[18:30] Hive ETL starting..."
hive -f /app/etl/ods_to_dwd.hql
hive -f /app/etl/dwd_to_dws.hql

# 步骤3: HBase 兜底数据同步
echo "[19:30] HBase sync starting..."
python /app/hbase_sync.py

# 步骤4: 复盘数据预热到 Redis
echo "[19:45] Redis warmup starting..."
python /app/hdfs_to_redis.py --review

echo "[20:00] Daily review ready!"
```

---

## 八、redis-python 支持说明

经验证 `redis-py` 已在宿主机可用，`hdfs_to_redis.py` 和 `hbase_sync.py` 可直接使用标准的 `redis.Redis(host='localhost', port=6379)` 连接 Redis。

依赖：
```bash
pip install redis happybase pyarrow pandas
```

---

## 九、实施路线

| 步 | 内容 | 预计耗时 |
|----|------|---------|
| 1 | docker-compose 添加 HDFS + Hive + HBase 共 7 个容器 | 1.5h |
| 2 | `hdfs_upload.py` 改造：首次全量同步 5 年 K 线到 HDFS Parquet | 1h |
| 3 | Hive DDL 创建 ODS 外部表 | 0.5h |
| 4 | Hive ETL 脚本：ODS→DWS（行业轮动/资金汇总/技术扫描） | 1h |
| 5 | HBase `stock_fallback` 表 + hbase_sync.py 同步脚本 | 1h |
| 6 | `hdfs_to_redis.py` 改造 + 后端兜底接口 `/fallback/{code}` | 0.5h |
| 7 | 前端"每日复盘"大屏页面 + 20:00 通知 | 0.5h |
| **总计** | | **~6h** |

---

## 十、与毕设考核点对照

| 考核点 | 本方案体现 |
|-------|-----------|
| **HDFS 分布式存储** | 7 种类型数据（K线/行情/信号/指数/资讯等）以 Parquet 格式存储在 HDFS，按 dt 分区 |
| **Hive 数仓建模** | ODS→DWD→DWS→ADS 四层结构，分区表 + 外部表 + Pivot SQL |
| **HBase 列式存储** | RowKey 反转设计，30 天 K 线 + 价格快照宽表，支撑实时回退 |
| **Lambda 架构** | 速度层(Redis/WS) + 批处理层(Hive) + 服务层(HBase) 完整闭环 |
| **大数据 ETL** | Hive SQL 批处理：行业轮动Pivot、技术扫描、资金汇总 |
| **数据合并** | 实时 Redis + 离线 Hive 通过 hdfs_to_redis.py 在 Redis 层交汇 |
| **前端可视化** | 每日复盘大屏：热力图/条形图/折线图/圆环图/卡片综合展示 |
