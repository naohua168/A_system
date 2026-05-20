package com.stock.config;

import com.stock.security.JwtUtil;
import com.stock.security.SecurityLevelService;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

import static org.mockito.Mockito.mock;

/**
 * @WebMvcTest 测试配置 — Mock SecurityLevelService + JwtUtil 依赖
 *
 * 解决: @WebMvcTest 不加载 @Service bean,
 * 但 WebMvcConfig 的 PermissionInterceptor 依赖 SecurityLevelService,
 * 且 JwtFilter 依赖 JwtUtil.
 */
@TestConfiguration
public class WebMvcTestConfig {

    @Bean
    @Primary
    public SecurityLevelService securityLevelService() {
        return mock(SecurityLevelService.class);
    }

    @Bean
    @Primary
    public JwtUtil jwtUtil() {
        return mock(JwtUtil.class);
    }
}
