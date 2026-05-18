# ============================================================
# Frontend — Vue 3 生产 Dockerfile
# 多阶段构建（总镜像 < 30MB）
# 修复: context=项目根目录，COPY路径加 frontend/ 前缀
# ============================================================

# ---- 构建阶段 ----
FROM node:20-alpine AS builder

WORKDIR /build

# 1. 先拷贝依赖文件，利用 Docker 缓存层
COPY frontend/package*.json ./
RUN npm ci --only=production && \
    cp -r node_modules /prod_modules && \
    npm ci

# 2. 拷贝源码并构建
COPY frontend/ ./
RUN npm run build

# ---- 运行阶段 ----
FROM nginx:1.25-alpine

# Nginx alpine 镜像已有 nginx 用户
RUN rm -f /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

# 拷贝生产级 nginx 配置
COPY docker/frontend/nginx.prod.conf /etc/nginx/conf.d/default.conf

# 设置严格权限
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

# 切换到 nginx 非 root 用户
USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]