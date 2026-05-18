# ============================================================
# Data Collector — Python 数据采集器 Dockerfile (v2)
# 修复: 使用系统级 pip install 而非 --user，确保非 root 用户 collector 可导入
# ============================================================

# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .
# 修复: 使用系统级安装 (不使用 --user)，确保所有用户可访问
RUN pip install --no-cache-dir -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    addgroup --system --gid 1000 collector && \
    adduser --system --uid 1000 --ingroup collector collector

WORKDIR /app

# 修复: 直接从 builder 的 site-packages 复制，而非从 /root/.local
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN mkdir -p /app/logs /data/raw && \
    chown -R collector:collector /app /data && \
    chmod -R 755 /app

USER collector:collector

VOLUME ["/data/raw", "/app/logs"]

CMD ["python", "scheduler/run_collector.py"]
