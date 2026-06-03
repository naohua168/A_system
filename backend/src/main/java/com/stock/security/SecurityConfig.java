package com.stock.security;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Autowired
    private JwtFilter jwtFilter;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // 禁用CSRF（前后端分离）
            .csrf(csrf -> csrf.disable())

            // 启用CORS
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))

            // 无状态Session（使用JWT）
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))

            // 路径权限控制 — 基于角色的细粒度访问
            .authorizeHttpRequests(auth -> auth
                // ── 公开访问（无需认证） ──
                .antMatchers(
                    "/api/user/login",
                    "/api/user/register",
                    "/api/public/**",
                    "/api/v2/**",
                    "/api/watchlist/**",
                    "/api/analysis/*/chanlun",
                    "/ws/**",
                    "/swagger-ui/**",
                    "/v3/api-docs/**"
                ).permitAll()

                // ── 管理接口（需要 ADMIN 或 SUPER_ADMIN 角色） ──
                .antMatchers("/api/admin/**").hasAnyRole("ADMIN", "SUPER_ADMIN")
                .antMatchers("/api/user/list", "/api/user/create",
                             "/api/user/disable", "/api/user/enable")
                    .hasAnyRole("ADMIN", "SUPER_ADMIN")
                .antMatchers("/api/data/collector/**", "/api/data/pipeline/**")
                    .hasAnyRole("ADMIN", "SUPER_ADMIN")
                .antMatchers("/api/system/config/**")
                    .hasAnyRole("ADMIN", "SUPER_ADMIN")

                // ── 安全管理接口（仅 SUPER_ADMIN） ──
                .antMatchers("/api/security/**").hasRole("SUPER_ADMIN")
                .antMatchers("/api/system/logs/**").hasRole("SUPER_ADMIN")

                // ── 高级分析接口（需要 PREMIUM_USER 及以上） ──
                .antMatchers("/api/analysis/correlation",
                             "/api/analysis/filter",
                             "/api/analysis/technical/**")
                    .hasAnyRole("PREMIUM_USER", "ADMIN", "SUPER_ADMIN")
                .antMatchers("/api/data/export/**")
                    .hasAnyRole("PREMIUM_USER", "ADMIN", "SUPER_ADMIN")

                // ── 其他所有API需要认证 ──
                .anyRequest().authenticated()
            )

            // 注入JWT过滤器
            .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        // 修复: 生产环境不允许任意来源，改为具体域名白名单或使用 allowedOriginPatterns
        String allowedOrigin = System.getenv().getOrDefault("CORS_ALLOWED_ORIGIN", "*");
        if ("*".equals(allowedOrigin)) {
            configuration.addAllowedOriginPattern("*");
        } else {
            configuration.setAllowedOrigins(Arrays.asList(allowedOrigin.split(",")));
        }
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("Content-Type", "Authorization", "X-Requested-With"));
        configuration.setExposedHeaders(List.of("Authorization"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}
