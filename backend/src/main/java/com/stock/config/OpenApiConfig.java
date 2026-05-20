package com.stock.config;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Contact;
import io.swagger.v3.oas.annotations.info.Info;
import io.swagger.v3.oas.annotations.info.License;
import io.swagger.v3.oas.annotations.servers.Server;
import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * OpenAPI 3.0 文档配置
 *
 * 访问地址: http://localhost:8082/swagger-ui.html
 * JSON 地址: http://localhost:8082/v3/api-docs
 */
@OpenAPIDefinition(
    info = @Info(
        title = "基金股票智能分析系统 API",
        version = "2.2.0",
        description = """
            六层架构金融智能分析平台 REST API。
            
            层架构:
            - L1: 数据采集层 (Python)
            - L2: 大数据处理层 (Hive+Spark)
            - L3: 算法分析层 (技术指标+缠论+量化)
            - L4: 后端 API 层 (Spring Boot) ← 当前文档
            - L5: AI 智能服务层 (FastAPI)
            - L6: 前端展示层 (Vue 3)
            
            认证方式: Bearer JWT Token
            统一响应: { code, message, data, timestamp }
            """,
        contact = @Contact(
            name = "开发团队",
            email = "dev@example.com"
        ),
        license = @License(
            name = "MIT",
            url = "https://opensource.org/licenses/MIT"
        )
    ),
    servers = {
        @Server(url = "http://localhost:8082", description = "本地开发"),
        @Server(url = "http://backend:8082", description = "Docker 内部"),
    },
    tags = {
        @Tag(name = "Market", description = "市场行情 API"),
        @Tag(name = "Analysis", description = "分析 API (收益率/趋势/筛选/缠论)"),
        @Tag(name = "Fund", description = "基金 API"),
        @Tag(name = "Signal", description = "信号数据 API (热点/北向/龙虎榜)"),
        @Tag(name = "Info", description = "资讯 API (研报/新闻/公告)"),
        @Tag(name = "Index", description = "指数 API"),
        @Tag(name = "User", description = "用户 API (登录/注册/管理)"),
        @Tag(name = "Watchlist", description = "自选股 API"),
        @Tag(name = "AI", description = "AI 对话 API"),
        @Tag(name = "Layers", description = "系统架构 API"),
    }
)
public class OpenApiConfig {
    // 配置由 @OpenAPIDefinition 注解自动处理
}
