package com.stock.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    @Value("${jwt.secret:DefaultSecretKeyForAStockSystem2026DevEnvironment}")
    private String secret;

    @Value("${jwt.expiration:86400000}")
    private long expiration; // 默认24小时

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * 生成JWT Token
     * @param userId 用户ID
     * @param username 用户名
     * @return JWT Token字符串
     */
    public String generateToken(Long userId, String username) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expiration);

        return Jwts.builder()
                .setSubject(userId.toString())
                .claim("username", username)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
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
     * @param token JWT Token
     * @return 用户ID
     */
    public Long getUserId(String token) {
        Claims claims = validateToken(token);
        return Long.parseLong(claims.getSubject());
    }

    /**
     * 从Token获取用户名
     * @param token JWT Token
     * @return 用户名
     */
    public String getUsername(String token) {
        Claims claims = validateToken(token);
        return claims.get("username", String.class);
    }

    /**
     * 判断Token是否过期
     * @param token JWT Token
     * @return true=已过期
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
