#!/bin/bash
# ============================================================
# 一键启动所有服务 (Mac/Linux)
# ============================================================
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 启动基金股票智能分析系统..."
echo "================================"

# 1. 启动 Docker 大数据环境
echo ""
echo "📦 [1/4] 启动 Docker 环境..."
cd "$ROOT_DIR/docker"
docker-compose up -d 2>/dev/null || docker compose up -d
echo "   ✅ Docker 启动中 (hadoop/hive/mysql)"

# 2. 启动后端
echo ""
echo "🔙 [2/4] 启动 Spring Boot 后端..."
cd "$ROOT_DIR/backend"
mvn spring-boot:run -q &
BACKEND_PID=$!
echo "   ✅ 后端启动中 (PID: $BACKEND_PID)"

# 3. 启动前端
echo ""
echo "🎨 [3/4] 启动 Vue 前端..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "   ✅ 前端启动中 (PID: $FRONTEND_PID)"

# 4. 验证
echo ""
echo "⏳ [4/4] 等待服务就绪..."
sleep 10
echo ""
echo "================================"
echo "✅ 系统启动完成!"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8080"
echo "   HDFS: http://localhost:9870"
echo "   Hive: jdbc:hive2://localhost:10000"
echo "================================"

# 保存 PID 以便 stop-all 使用
echo "$BACKEND_PID" > /tmp/stock-backend.pid
echo "$FRONTEND_PID" > /tmp/stock-frontend.pid
