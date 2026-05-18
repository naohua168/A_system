#!/bin/bash
# ============================================================
# 采集数据 → HDFS 批量导入脚本
# 将采集层共享卷中的 CSV 数据导入 HDFS
# ============================================================
# 数据流: collector-data (共享卷) → HDFS
#
# 用法:
#   ./ingest_collector_data.sh              # 导入全部
#   ./ingest_collector_data.sh --daily      # 仅导入日K线
#   ./ingest_collector_data.sh --dry-run    # 仅预览
# ============================================================

NAMENODE_CONTAINER="namenode"
COLLECTOR_DATA_DIR="/data/collector_output"
HDFS_BASE="/user/hadoop/stock_data"

# 文件映射：采集层 CSV → HDFS 目标目录
declare -A FILE_MAP
FILE_MAP["stock_daily_*.csv"]="$HDFS_BASE/daily"
FILE_MAP["stock_basic_*.csv"]="$HDFS_BASE/basic"
FILE_MAP["fund_nav_*.csv"]="$HDFS_BASE/fund/nav"
FILE_MAP["fund_basic_*.csv"]="$HDFS_BASE/fund/basic"

DRY_RUN=false
MODE="all"

# 解析参数
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --daily|--basic|--fund) MODE="${arg#--}" ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

echo "========================================"
echo "📥 采集数据 → HDFS 导入"
echo "   模式: $MODE"
echo "   预览: $DRY_RUN"
echo "========================================"

imported=0
for pattern in "${!FILE_MAP[@]}"; do
    hdfs_dir="${FILE_MAP[$pattern]}"

    # 模式过滤
    case $MODE in
        daily)   [[ "$pattern" != *daily* ]] && continue ;;
        basic)   [[ "$pattern" != *basic* ]] && continue ;;
        fund)    [[ "$pattern" != *fund* ]] && continue ;;
    esac

    # 检查采集层文件是否存在
    file_count=$(docker exec "$NAMENODE_CONTAINER" bash -c \
        "ls $COLLECTOR_DATA_DIR/$pattern 2>/dev/null | wc -l")

    if [ "$file_count" -eq 0 ]; then
        echo "  - $pattern: 无文件"
        continue
    fi

    # 创建 HDFS 目录
    docker exec "$NAMENODE_CONTAINER" bash -c \
        "hdfs dfs -mkdir -p $hdfs_dir" 2>/dev/null

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] $COLLECTOR_DATA_DIR/$pattern → $hdfs_dir/"
    else
        echo "  📄 $pattern ($file_count 文件) → $hdfs_dir/"
        docker exec "$NAMENODE_CONTAINER" bash -c \
            "hdfs dfs -put -f $COLLECTOR_DATA_DIR/$pattern $hdfs_dir/" 2>&1
        if [ $? -eq 0 ]; then
            echo "    ✅ 导入成功"
            ((imported++))
        else
            echo "    ❌ 导入失败"
        fi
    fi
done

# 验证
if [ "$DRY_RUN" = false ]; then
    echo ""
    echo "📊 HDFS 数据验证:"
    docker exec "$NAMENODE_CONTAINER" bash -c \
        "hdfs dfs -du -h $HDFS_BASE 2>/dev/null" || echo "  (空)"
fi

echo ""
echo "✅ 导入完成: $imported 组文件"
echo "========================================"
