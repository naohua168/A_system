package com.stock.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Redis 数据读取器 — 从 Redis 读取行情/信号/资讯数据
 * Redis 不可用时自动降级到 MySQL stock_history 兜底
 */
@Service
public class RedisReader {

    private static final Logger log = LoggerFactory.getLogger(RedisReader.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired(required = false)
    private StringRedisTemplate redisTemplate;

    @Autowired(required = false)
    @Qualifier("historyJdbcTemplate")
    private JdbcTemplate historyJdbc;

    /** Redis key → MySQL table 映射（用于降级查询） */
    private static final Map<String, String> KEY_TABLE_MAP = Map.of(
        "market:stock_basic", "stock_daily",
        "market:index_list", "index_daily",
        "market:industry_compare", "industry_daily",
        "market:northbound", "northbound_daily",
        "market:hot_reason", "hot_reason_daily",
        "market:dragon_tiger", "dragon_tiger_daily"
    );

    /** 从 Redis 读取指定 key 的 JSON 数据，反序列化为 List<Map> */
    public List<Map<String, Object>> getAsList(String key) {
        // 1) 优先 Redis
        if (redisTemplate != null) {
            try {
                String json = redisTemplate.opsForValue().get(key);
                if (json != null && !json.isBlank() && !"[]".equals(json)) {
                    return MAPPER.readValue(json,
                        MAPPER.getTypeFactory().constructCollectionType(List.class, Map.class));
                }
            } catch (Exception e) {
                log.warn("Redis 读取失败 (key={}), 尝试 MySQL 降级", key);
            }
        }
        // 2) Redis 不可用 → MySQL 降级
        return fallbackToMysql(key);
    }

    public String getAsJson(String key) {
        if (redisTemplate != null) {
            try {
                String json = redisTemplate.opsForValue().get(key);
                if (json != null && !json.isBlank()) return json;
            } catch (Exception e) {
                log.warn("Redis getAsJson 失败 (key={})", key);
            }
        }
        return "[]";
    }

    /** 批量读取多个 key（Redis MGET） */
    public List<String> multiGet(List<String> keys) {
        if (redisTemplate == null || keys == null || keys.isEmpty()) return Collections.emptyList();
        try {
            List<String> result = redisTemplate.opsForValue().multiGet(keys);
            return result != null ? result : Collections.emptyList();
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    /** MySQL 降级：查询 stock_history 对应表的最新数据 */
    private List<Map<String, Object>> fallbackToMysql(String key) {
        String table = KEY_TABLE_MAP.get(key);
        if (table == null || historyJdbc == null) return Collections.emptyList();
        try {
            String sql = "SELECT * FROM " + table + " WHERE trade_date = (SELECT MAX(trade_date) FROM " + table + ") LIMIT 1000";
            List<Map<String, Object>> result = historyJdbc.queryForList(sql);
            if (!result.isEmpty()) {
                log.info("✅ MySQL 降级成功: key={}, table={}, rows={}", key, table, result.size());
            }
            return result;
        } catch (DataAccessException e) {
            log.warn("MySQL 降级失败: key={}, table={}, error={}", key, table, e.getMessage());
            return Collections.emptyList();
        }
    }
}
