#!/bin/bash
# ============================================================
# 一键启动所有服务 (优化版 — 双层架构)
# ============================================================
# 先启动大数据层（HDFS/Hive/Spark/MySQL/Redis）
# 可选: 使用 docker-compose.collector.yml 启动采集层
# 可选: 执行 Hive TEXTFILE → ORC 自动迁移
#
# 用法:
#   ./start-all.sh              # 仅大数据层
#   ./start-all.sh --full       # 全量（含采集层）
#   ./start-all.sh --full --migrate-orc  # 全量 + ORC 迁移
#   ./start-all.sh --collector-only  # 仅采集层
#   ./start-all.sh --bigdata-only    # 仅大数据层
#   ./start-all.sh --migrate-orc     # 仅大数据层 + ORC 迁移
# ============================================================

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_DIR="$ROOT_DIR/docker"

MODE="bigdata-only"
MIGRATE_ORC=false

for arg in "$@"; do
    case "$arg" in
        --full|full|--all|all) MODE="full" ;;
        --collector-only|collector) MODE="collector" ;;
        --bigdata-only|bigdata) MODE="bigdata" ;;
        --migrate-orc|migrate_orc) MIGRATE_ORC=true ;;
    esac
done

echo "============================================================"
echo "🚀 基金股票智能分析系统 — 分层部署"
echo "   ORC 迁移: $([ "$MIGRATE_ORC" = true ] && echo '✅ 启用' || echo '⏭️  跳过')"
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

migrate_orc_tables() {
    echo ""
    echo "🗃️  [ORC 迁移] 检查 Hive 并执行 TEXTFILE → ORC 自动迁移..."
    MIGRATE_SCRIPT="$ROOT_DIR/bigdata-processing/scripts/migrate_hive_to_orc.py"

    if [ ! -f "$MIGRATE_SCRIPT" ]; then
        echo "   ⚠️  迁移脚本不存在: $MIGRATE_SCRIPT"
        return 1
    fi

    # 等待 Hive 服务就绪（最多等 60 秒）
    echo "   ⏳ 等待 Hive 服务就绪..."
    for i in $(seq 1 12); do
        if docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;" &>/dev/null; then
            echo "   ✅ Hive 服务已就绪"
            break
        fi
        sleep 5
    done

    echo "   🔄 执行 ORC 迁移..."
    python "$MIGRATE_SCRIPT" --resume 2>&1 || echo "   ⚠️  ORC 迁移完成（部分表可能已存在）"
    echo "   ✅ ORC 迁移流程结束"
}

case "$MODE" in
    --collector-only|collector)
        start_collector
        ;;
    --bigdata-only|bigdata)
        start_bigdata
        if [ "$MIGRATE_ORC" = true ]; then
            migrate_orc_tables
        fi
        ;;
    --full|full|--all|all)
        # 采集层先启动（Kafka需先就绪，大数据层Spark消费）
        start_collector
        echo ""
        echo "⏳ 等待 Kafka 就绪..."
        sleep 10
        start_bigdata
        if [ "$MIGRATE_ORC" = true ]; then
            migrate_orc_tables
        fi
        ;;
    *)
        echo "用法: $0 [--full|--collector-only|--bigdata-only] [--migrate-orc]"
        echo "  默认: --bigdata-only | 附加 --migrate-orc 执行 ORC 迁移"
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
