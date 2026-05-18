#!/bin/bash
# ============================================================
# 一键启动所有服务 (优化版 — 双层架构)
# ============================================================
# 先启动大数据层（HDFS/Hive/Spark/MySQL/Redis）
# 可选: 使用 docker-compose.collector.yml 启动采集层
#
# 用法:
#   ./start-all.sh              # 仅大数据层
#   ./start-all.sh --full       # 全量（含采集层）
#   ./start-all.sh --collector-only  # 仅采集层
#   ./start-all.sh --bigdata-only    # 仅大数据层
# ============================================================

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_DIR="$ROOT_DIR/docker"

MODE="${1:-bigdata-only}"

echo "============================================================"
echo "🚀 基金股票智能分析系统 — 分层部署"
echo "============================================================"

start_collector() {
    echo ""
    echo "📡 [采集层] 启动数据采集服务..."
    cd "$DOCKER_DIR"
    docker compose -f docker-compose.collector.yml up -d
    echo "   ✅ Zookeeper + Kafka + DataCollector"
}

start_bigdata() {
    echo ""
    echo "📦 [大数据层] 启动大数据服务..."
    cd "$DOCKER_DIR"

    # 尝试叠加 prod.yml（如果存在）
    COMPOSE_FILES="-f docker-compose.yml"
    if [ -f docker-compose.prod.yml ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
        echo "   📋 叠加生产配置"
    fi

    docker compose $COMPOSE_FILES up -d
    echo "   ✅ HDFS + YARN + Hive + Spark + MySQL + Redis + App"
}

case "$MODE" in
    --collector-only|collector)
        start_collector
        ;;
    --bigdata-only|bigdata)
        start_bigdata
        ;;
    --full|full|--all|all)
        # 采集层先启动（Kafka需先就绪，大数据层Spark消费）
        start_collector
        echo ""
        echo "⏳ 等待 Kafka 就绪..."
        sleep 10
        start_bigdata
        ;;
    *)
        echo "用法: $0 [--full|--collector-only|--bigdata-only]"
        echo "  默认: --bigdata-only"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "✅ 部署完成!"
echo "============================================================"
echo ""
echo "Web UI:"
echo "  前端:       http://localhost:80"
echo "  HDFS:       http://localhost:9870"
echo "  YARN:       http://localhost:8088"
echo "  Hive:       http://localhost:10002"
echo "  Spark:      http://localhost:8080"
echo ""
echo "服务端口:"
echo "  后端 API:   http://localhost:8082"
echo "  AI 服务:    http://localhost:8000"
echo "  MySQL:      localhost:3306"
echo "  Redis:      localhost:6379"
echo ""
echo "数据流:"
echo "  采集层 → Kafka(collector-kafka:29092) → 大数据层(Streaming)"
echo "  采集层 → 共享卷(/data/collector_output) → HDFS"
echo "============================================================"
