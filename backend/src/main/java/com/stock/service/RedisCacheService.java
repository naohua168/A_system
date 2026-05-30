package com.stock.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

/**
 * Redis 缓存服务 — 缓存优先 + Hive 回查
 *
 * 所有市场数据 API 通过此服务读取数据，不直接读 MySQL。
 * 流程: Redis GET → 命中则返回 → 未命中则 Hive 查询 → Redis SETEX → 返回
 */
@Service
public class RedisCacheService {

    private static final Logger log = LoggerFactory.getLogger(RedisCacheService.class);
    private static final long DEFAULT_TTL_SECONDS = 60;

    @Autowired(required = false)
    private StringRedisTemplate redisTemplate;

    @Autowired(required = false)
    @Qualifier("hiveJdbcTemplate")
    private JdbcTemplate hiveJdbc;

    /**
     * 从缓存读取，未命中则通过 Hive 查询并写入缓存
     *
     * @param cacheKey Redis key
     * @param hiveSql  Hive SQL 查询
     * @param ttl      缓存过期时间（秒）
     * @return JSON 字符串
     */
    public String getOrFetch(String cacheKey, String hiveSql, long ttl) {
        // 1. 尝试从 Redis 读取
        if (redisTemplate != null) {
            try {
                String cached = redisTemplate.opsForValue().get(cacheKey);
                if (cached != null) {
                    return cached;
                }
            } catch (Exception e) {
                log.warn("Redis 读取失败({}), 回查 Hive", e.getMessage());
            }
        }

        // 2. 回查 Hive
        if (hiveJdbc == null) {
            log.warn("Hive JDBC 未配置, 返回空");
            return "[]";
        }
        try {
            String result = queryHive(hiveSql);
            // 3. 写入 Redis 缓存
            if (redisTemplate != null && result != null) {
                try {
                    redisTemplate.opsForValue().set(cacheKey, result, ttl, TimeUnit.SECONDS);
                } catch (Exception e) {
                    log.warn("Redis 写入失败: {}", e.getMessage());
                }
            }
            return result;
        } catch (Exception e) {
            log.error("Hive 查询失败: {} - {}", hiveSql.substring(0, Math.min(80, hiveSql.length())), e.getMessage());
            return "[]";
        }
    }

    /** 简化版：使用默认 TTL */
    public String getOrFetch(String cacheKey, String hiveSql) {
        return getOrFetch(cacheKey, hiveSql, DEFAULT_TTL_SECONDS);
    }

    /** 手动查询 Hive */
    public String queryHive(String sql) {
        if (hiveJdbc == null) return "[]";
        try {
            java.util.List<java.util.Map<String, Object>> rows = hiveJdbc.queryForList(sql);
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(rows);
        } catch (Exception e) {
            log.error("Hive 查询异常: {}", e.getMessage());
            return "[]";
        }
    }

    /** 手动清除缓存 */
    public void evict(String cacheKey) {
        if (redisTemplate != null) {
            try {
                redisTemplate.delete(cacheKey);
            } catch (Exception ignored) {}
        }
    }
}
