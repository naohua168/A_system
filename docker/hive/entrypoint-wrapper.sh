#!/bin/bash

# 清理 Derby 锁文件（防止上次异常关闭导致锁残留）
  rm -f /opt/hive/metastore_db/db.lck /opt/hive/metastore_db/dbex.lck 2>/dev/null

# 等待 HDFS NameNode 就绪（最多重试 30 次）
for i in $(seq 1 30); do
  hadoop fs -ls / >/dev/null 2>&1 && break
  echo "[$(date)] Waiting for NameNode... ($i/30)"
  sleep 2
done

# 创建 HDFS 目录
hadoop fs -mkdir -p /tmp
hadoop fs -mkdir -p /user/hive/warehouse
hadoop fs -chmod g+w /tmp
hadoop fs -chmod g+w /user/hive/warehouse

# 初始化 Hive Metastore schema（使用 MySQL）
/opt/hive/bin/schematool -initSchema -dbType mysql 2>&1 | grep -v SLF4J || true

# 再次清理 Derby 锁文件（schematool 运行后可能残留）
rm -f /opt/hive/metastore_db/db.lck /opt/hive/metastore_db/dbex.lck

# 启动 HiveServer2（NOSASL 模式，兼容 DataGrip 等外部 JDBC 客户端）
cd /opt/hive/bin
exec ./hiveserver2 \
  --hiveconf hive.server2.enable.doAs=false \
  --hiveconf hive.server2.authentication=NONE
