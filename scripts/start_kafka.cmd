@echo off
cd /d f:\bs\A_system\docker
echo [1/4] 拉取 Zookeeper 镜像...
docker pull docker.1ms.run/confluentinc/cp-zookeeper:7.5.0
echo [2/4] 拉取 Kafka 镜像...
docker pull docker.1ms.run/confluentinc/cp-kafka:7.5.0
echo [3/4] 打标签...
docker tag docker.1ms.run/confluentinc/cp-zookeeper:7.5.0 confluentinc/cp-zookeeper:7.5.0
docker tag docker.1ms.run/confluentinc/cp-kafka:7.5.0 confluentinc/cp-kafka:7.5.0
echo [4/4] 启动容器...
docker compose up -d zookeeper kafka
echo.
echo === 运行中的容器 ===
docker compose ps --filter status=running
pause
