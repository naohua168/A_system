package com.stock.config;

import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import io.github.resilience4j.timelimiter.TimeLimiterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.time.Duration;
import java.util.concurrent.TimeoutException;

/**
 * Resilience4j 熔断器配置
 *
 * 保护外部依赖调用（如 AI 服务、数据库查询），防止级联故障。
 * 熔断状态: CLOSED(正常) → OPEN(熔断) → HALF_OPEN(半开) → CLOSED
 */
@Configuration
public class ResilienceConfig {

    private static final Logger log = LoggerFactory.getLogger(ResilienceConfig.class);

    /**
     * 默认熔断器配置:
     * - slidingWindowSize: 10   计数窗口大小（最近10次调用）
     * - failureRateThreshold: 50  失败率阈值（50%）
     * - waitDurationInOpenState: 10s  熔断持续时间
     * - permittedNumberOfCallsInHalfOpenState: 3  半开态允许的调用数
     */
    @Bean
    public CircuitBreakerConfig defaultCircuitBreakerConfig() {
        return CircuitBreakerConfig.custom()
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(10)
                .minimumNumberOfCalls(5)
                .failureRateThreshold(50)
                .waitDurationInOpenState(Duration.ofSeconds(10))
                .permittedNumberOfCallsInHalfOpenState(3)
                .recordExceptions(IOException.class, RuntimeException.class)
                .build();
    }

    /**
     * AI 服务专用熔断器配置（AI 响应较慢，容忍度更高）
     */
    @Bean
    public CircuitBreakerConfig aiServiceCircuitBreakerConfig() {
        return CircuitBreakerConfig.custom()
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(20)
                .minimumNumberOfCalls(10)
                .failureRateThreshold(60)        // AI 服务允许更高失败率
                .slowCallRateThreshold(50)        // 慢调用阈值
                .slowCallDurationThreshold(Duration.ofSeconds(30))  // 30s 以上算慢
                .waitDurationInOpenState(Duration.ofSeconds(30))    // AI 恢复更慢
                .permittedNumberOfCallsInHalfOpenState(5)
                .recordExceptions(IOException.class, RuntimeException.class, TimeoutException.class)
                .build();
    }

    /**
     * AI 服务超时配置
     */
    @Bean
    public TimeLimiterConfig aiServiceTimeLimiterConfig() {
        return TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(60))
                .cancelRunningFuture(true)
                .build();
    }

    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry(
            CircuitBreakerConfig defaultConfig,
            CircuitBreakerConfig aiServiceConfig) {
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.of(defaultConfig);
        registry.circuitBreaker("ai-service", aiServiceConfig);
        log.info("熔断器注册完成: 默认={}, AI服务={}",
                "slidingWindowSize=10, failureRateThreshold=50%",
                "slidingWindowSize=20, failureRateThreshold=60%");
        return registry;
    }

    @Bean
    public TimeLimiterRegistry timeLimiterRegistry(TimeLimiterConfig aiServiceConfig) {
        TimeLimiterRegistry registry = TimeLimiterRegistry.of(aiServiceConfig);
        log.info("超时限制器注册完成: timeout=60s");
        return registry;
    }
}
