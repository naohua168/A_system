#!/bin/bash

# 创建 HDFS 目录
hadoop fs -mkdir -p /tmp
hadoop fs -mkdir -p /user/hive/warehouse
hadoop fs -chmod g+w /tmp
hadoop fs -chmod g+w /user/hive/warehouse

# 初始化 Hive Metastore schema（首次启动时创建）
/opt/hive/bin/schematool -initSchema -dbType derby 2>&1 | grep -v SLF4J | grep -v "already exists" || true

# 启动 HiveServer2
cd /opt/hive/bin
exec ./hiveserver2 --hiveconf hive.server2.enable.doAs=false
