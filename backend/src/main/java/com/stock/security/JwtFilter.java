package com.stock.security;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import io.jsonwebtoken.Claims;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

@Component
public class JwtFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(JwtFilter.class);

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired(required = false)
    private StringRedisTemplate redisTemplate;

    /** 白名单路径 — 无需认证即可访问 */
    private static final List<String> WHITE_LIST = Arrays.asList(
            "/api/user/login",
            "/api/user/register",
            "/api/public/**",
            "/swagger-ui/**",
            "/v3/api-docs/**"
    );

    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain)
            throws ServletException, IOException {

        String authHeader = request.getHeader("Authorization");

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            // 修复: 增加空 Token 判断，避免空串传入 JWT 解析库
            if (token.isEmpty()) {
                filterChain.doFilter(request, response);
                return;
            }

            try {
                // 修复: 只解析 JWT 一次，提取所有 Claims 后复用
                // 原代码每次请求解析 JWT 四次 (isTokenExpired/getUserId/getUsername/getUserRole)
                io.jsonwebtoken.Claims claims = jwtUtil.validateToken(token);

                // 检查 Redis 黑名单（登出的 token 立即失效）
                if (redisTemplate != null && Boolean.TRUE.equals(
                        redisTemplate.hasKey("blacklist:" + token))) {
                    SecurityContextHolder.clearContext();
                    filterChain.doFilter(request, response);
                    return;
                }

                Long userId = Long.parseLong(claims.getSubject());
                String username = claims.get("username", String.class);
                String roleStr = claims.get("role", String.class);
                UserRole role = UserRole.fromConfigId(roleStr);

                if (!claims.getExpiration().before(new java.util.Date())) {
                    // 构建包含角色信息的认证令牌
                    UsernamePasswordAuthenticationToken authentication =
                            new UsernamePasswordAuthenticationToken(
                                    username, null,
                                    Collections.singletonList(
                                            new SimpleGrantedAuthority("ROLE_" + role.getConfigId())
                                    )
                            );
                    authentication.setDetails(
                            new WebAuthenticationDetailsSource().buildDetails(request));

                    // 注入 SecurityContext (Spring Security)
                    SecurityContextHolder.getContext().setAuthentication(authentication);

                    // 注入 Request Attribute (权限拦截器使用)
                    request.setAttribute("userId", userId);
                    request.setAttribute("username", username);
                    request.setAttribute("userRole", role);
                }
            } catch (Exception e) {
                // 修复: 记录日志并清除 SecurityContext，防止前置过滤器残留认证信息导致权限提升
                log.warn("JWT 认证失败: {} - {}", e.getClass().getSimpleName(), e.getMessage());
                SecurityContextHolder.clearContext();
            }
        }

        filterChain.doFilter(request, response);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getServletPath();
        return WHITE_LIST.stream().anyMatch(pattern -> pathMatcher.match(pattern, path));
    }
}
