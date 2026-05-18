#!/bin/bash
# ============================================================
# Kafka Topic 初始化脚本
# ============================================================
set -e

KAFKA_CONTAINER="kafka"
KAFKA_BOOTSTRAP="localhost:9092"
PARTITIONS=1
REPLICATION=1

echo "=== 初始化 Kafka Topics ==="

declare -A TOPICS
TOPICS["raw_realtime"]="腾讯财经原始HTTP响应体 → Spark解析→MySQL+HDFS"
TOPICS["raw_kline"]="通达信原始K线数据 → Spark计算指标→存储"
TOPICS["raw_fund_nav"]="基金净值原始数据"
TOPICS["raw_news"]="财经新闻原始数据"
TOPICS["raw_filings"]="公告原始数据"

for topic in "${!TOPICS[@]}"; do
    desc="${TOPICS[$topic]}"
    echo ""
    echo "📌 $topic"
    echo "   $desc"

    docker exec "$KAFKA_CONTAINER" \
        kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" \
        --create --if-not-exists \
        --topic "$topic" \
        --partitions "$PARTITIONS" \
        --replication-factor "$REPLICATION" \
        --config retention.ms=604800000 \
        --config max.message.bytes=10485760 \
        2>/dev/null && echo "   ✅ 已创建" || echo "   ⚠️  创建失败"
done

echo ""
echo "=== 所有 Topic 列表 ==="
docker exec "$KAFKA_CONTAINER" \
    kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP" --list

echo ""
echo "✅ Kafka 初始化完成"
