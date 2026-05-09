#!/bin/bash
# ============================================================
# 一键停止所有服务
# ============================================================

echo "🛑 停止所有服务..."
echo "===================="

# 停止前端
if [ -f /tmp/stock-frontend.pid ]; then
    kill $(cat /tmp/stock-frontend.pid) 2>/dev/null && echo "   ✅ 前端已停止" || echo "   ⚠️  前端未运行"
    rm -f /tmp/stock-frontend.pid
fi

# 停止后端
if [ -f /tmp/stock-backend.pid ]; then
    kill $(cat /tmp/stock-backend.pid) 2>/dev/null && echo "   ✅ 后端已停止" || echo "   ⚠️  后端未运行"
    rm -f /tmp/stock-backend.pid
fi

# 停止 Docker
cd "$(dirname "$0")/../docker"
docker-compose down 2>/dev/null || docker compose down 2>/dev/null
echo "   ✅ Docker 环境已停止"

echo "===================="
echo "🏁 所有服务已停止"
