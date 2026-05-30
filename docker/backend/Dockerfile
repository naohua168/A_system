# ============================================================
# Backend — Spring Boot 生产 Dockerfile
# 多阶段构建优化（总镜像 < 200MB）
# ============================================================

# ---- 构建阶段 ----
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /build

# 1. 先拷贝依赖文件，利用 Docker 缓存层
#    仅 pom.xml 变更时才重新下载依赖
COPY pom.xml ./
RUN mvn dependency:go-offline -B -q || true

# 2. 拷贝源码并构建
COPY src ./src
RUN mvn clean package -DskipTests -B -q

# ---- 运行阶段 ----
FROM eclipse-temurin:17-jre-alpine

# 安装 curl (健康检查用) 并清理
RUN apk add --no-cache curl && \
    addgroup -S spring && \
    adduser -S spring -G spring -u 1000

WORKDIR /app

# 从构建阶段拷贝 JAR
COPY --from=builder /build/target/*.jar app.jar

# 创建日志目录并授权
RUN mkdir -p /app/logs && \
    chown -R spring:spring /app

# 切换到非 root 用户
USER spring:spring

# 安全：只读根文件系统
VOLUME ["/app/logs"]

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -sf http://localhost:8082/api/v2/ping || exit 1

ENTRYPOINT ["java", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-jar", "app.jar"]
