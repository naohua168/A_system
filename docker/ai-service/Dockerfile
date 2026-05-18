# ============================================================
# AI Service — FastAPI 生产 Dockerfile
# 多阶段构建（总镜像 < 200MB）
# 修复: 拷贝到系统 site-packages 确保非 root 用户可访问
# ============================================================

# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

WORKDIR /build

# 先拷贝依赖文件，利用 Docker 缓存层
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.11-slim

# 安装 curl (健康检查用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    addgroup --system --gid 1000 ai && \
    adduser --system --uid 1000 --ingroup ai ai

WORKDIR /app

# 从构建阶段拷贝系统 site-packages（而非 /root/.local，确保非 root 用户可访问）
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 拷贝应用代码（限定目录，避免打包不必要的文件）
COPY app/ ./app/
COPY .env.example ./

# 创建日志目录并授权
RUN mkdir -p /app/logs && \
    chown -R ai:ai /app && \
    chmod -R 755 /app

# 切换到非 root 用户
USER ai:ai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--limit-max-requests", "10000", \
     "--timeout-keep-alive", "30"]
