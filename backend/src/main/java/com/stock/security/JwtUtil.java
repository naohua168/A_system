package com.stock.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    private static final Logger log = LoggerFactory.getLogger(JwtUtil.class);

    @Value("${jwt.secret:DefaultSecretKeyForAStockSystem2026DevEnvironment}")
    private String secret;

    @Value("${jwt.expiration:86400000}")
    private long expiration; // 默认24小时

    @PostConstruct
    public void init() {
        // 修复: 移除未使用的 SecurityLevelService 注入，启动时检查是否使用默认密钥
        if ("DefaultSecretKeyForAStockSystem2026DevEnvironment".equals(secret)) {
            log.warn("⚠️ JWT 使用默认密钥！生产环境必须在 application.yml 中设置 jwt.secret");
        }
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * 生成JWT Token（含角色信息）
     * @param userId 用户ID
     * @param username 用户名
     * @param role 用户角色
     * @return JWT Token字符串
     */
    public String generateToken(Long userId, String username, UserRole role) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expiration);

        return Jwts.builder()
                .setSubject(userId.toString())
                .claim("username", username)
                .claim("role", role.getConfigId())
                .claim("roleLevel", role.getLevel())
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    /** 兼容旧方法（默认 USER 角色） */
    public String generateToken(Long userId, String username) {
        return generateToken(userId, username, UserRole.USER);
    }

    /**
     * 从Token中提取Claims
     * @param token JWT Token
     * @return Claims
     */
    public Claims validateToken(String token) {
        return Jwts.parser()
                .verifyWith(getSigningKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * 从Token获取用户ID
     */
    public Long getUserId(String token) {
        Claims claims = validateToken(token);
        return Long.parseLong(claims.getSubject());
    }

    /**
     * 从Token获取用户名
     */
    public String getUsername(String token) {
        Claims claims = validateToken(token);
        return claims.get("username", String.class);
    }

    /**
     * 从Token获取用户角色
     */
    public UserRole getUserRole(String token) {
        Claims claims = validateToken(token);
        String roleStr = claims.get("role", String.class);
        return UserRole.fromConfigId(roleStr);
    }

    /**
     * 从Token获取角色级别
     */
    public int getRoleLevel(String token) {
        Claims claims = validateToken(token);
        return claims.get("roleLevel", Integer.class);
    }

    /**
     * 判断Token是否过期
     */
    public boolean isTokenExpired(String token) {
        try {
            Claims claims = validateToken(token);
            return claims.getExpiration().before(new Date());
        } catch (Exception e) {
            return true;
        }
    }
}
