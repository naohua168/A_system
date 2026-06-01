package com.stock.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Redis 数据读取器 — 从 Redis 读取 Hive 管道预热的行情数据
 * 数据来源: Python Hive→Redis 管道 (每60秒同步一次)
 */
@Service
public class RedisReader {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired(required = false)
    private StringRedisTemplate redisTemplate;

    /** 从 Redis 读取指定 key 的 JSON 数据，反序列化为 List<Map> */
    public List<Map<String, Object>> getAsList(String key) {
        if (redisTemplate == null) return Collections.emptyList();
        try {
            String json = redisTemplate.opsForValue().get(key);
            if (json == null || json.isBlank()) return Collections.emptyList();
            return MAPPER.readValue(json, 
                MAPPER.getTypeFactory().constructCollectionType(List.class, Map.class));
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    public String getAsJson(String key) {
        if (redisTemplate == null) return "[]";
        try {
            String json = redisTemplate.opsForValue().get(key);
            return json != null ? json : "[]";
        } catch (Exception e) {
            return "[]";
        }
    }

    /** 批量读取多个 key（Redis MGET），返回与 keys 顺序对应的值列表 */
    public List<String> multiGet(List<String> keys) {
        if (redisTemplate == null || keys == null || keys.isEmpty()) return Collections.emptyList();
        try {
            List<String> result = redisTemplate.opsForValue().multiGet(keys);
            return result != null ? result : Collections.emptyList();
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }
}
