# ============================================================
# Data Collector — Python 数据采集器 Dockerfile (v4)
# 架构: 市场数据走大数据层(Redis←Hive), MySQL仅存业务数据
# ============================================================

# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl redis-tools \
    && rm -rf /var/lib/apt/lists/* && \
    addgroup --system --gid 1000 collector && \
    adduser --system --uid 1000 --ingroup collector collector

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN mkdir -p /app/logs /data/raw && \
    chown -R collector:collector /app /data && \
    chmod -R 755 /app

USER collector:collector

VOLUME ["/data/raw", "/app/logs"]

# 健康检查：用 redis-cli 验证 Redis 中有市场基础数据
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
  CMD redis-cli -h redis -p 6379 EXISTS market:stock_basic | grep -q '^1' || exit 1

# ── 架构说明: 市场数据走大数据层，MySQL 仅存业务数据 ──
# 采集→CSV→HDFS→Hive→Spark→hive_to_redis.py→Redis→前端
# MySQL 不再作为市场数据查询源，sync_to_mysql 已禁用
CMD ["python", "scheduler/run_collector.py", "--all", "--loop", "30"]
