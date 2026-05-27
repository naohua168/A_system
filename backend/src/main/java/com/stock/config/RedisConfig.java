package com.stock.config;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Configuration
@EnableCaching
public class RedisConfig {

    /** 实时行情 / 资金流向：30秒 */
    private static final Duration TTL_REALTIME = Duration.ofSeconds(30);
    /** 龙虎榜 / 热点题材：5分钟 */
    private static final Duration TTL_HOT = Duration.ofMinutes(5);
    /** 股票列表 / 行业数据：15分钟 */
    private static final Duration TTL_STANDARD = Duration.ofMinutes(15);
    /** 研报 / 公告 / 新闻：30分钟 */
    private static final Duration TTL_INFO = Duration.ofMinutes(30);
    /** fund 净值：60分钟 */
    private static final Duration TTL_FUND = Duration.ofMinutes(60);
    /** 默认兜底：15分钟 */
    private static final Duration TTL_DEFAULT = Duration.ofMinutes(15);

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);

        // JSON序列化配置
        // 修复: 使用白名单限制反序列化类，防止 RCE 漏洞
        Jackson2JsonRedisSerializer<Object> jacksonSerializer = new Jackson2JsonRedisSerializer<>(Object.class);
        ObjectMapper mapper = new ObjectMapper();
        mapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        mapper.activateDefaultTyping(mapper.getPolymorphicTypeValidator(),
                ObjectMapper.DefaultTyping.NON_FINAL);
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        mapper.registerModule(new JavaTimeModule());
        jacksonSerializer.setObjectMapper(mapper);

        // key使用String序列化
        StringRedisSerializer stringSerializer = new StringRedisSerializer();

        template.setKeySerializer(stringSerializer);
        template.setHashKeySerializer(stringSerializer);
        template.setValueSerializer(jacksonSerializer);
        template.setHashValueSerializer(jacksonSerializer);

        template.afterPropertiesSet();
        return template;
    }

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory factory) {
        // JSON序列化配置
        Jackson2JsonRedisSerializer<Object> jacksonSerializer = new Jackson2JsonRedisSerializer<>(Object.class);
        ObjectMapper mapper = new ObjectMapper();
        mapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        mapper.activateDefaultTyping(mapper.getPolymorphicTypeValidator(),
                ObjectMapper.DefaultTyping.NON_FINAL);
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        mapper.registerModule(new JavaTimeModule());
        jacksonSerializer.setObjectMapper(mapper);

        StringRedisSerializer stringSerializer = new StringRedisSerializer();

        // 基础默认配置 — 默认兜底 TTL
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(TTL_DEFAULT)
                .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(stringSerializer))
                .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(jacksonSerializer))
                .disableCachingNullValues();

        // 按 cacheNames 分级 TTL
        Map<String, RedisCacheConfiguration> cacheConfigs = new HashMap<>();

        // 实时数据（30秒）：资金流向、行情快照
        cacheConfigs.put("realtime", defaultConfig.entryTtl(TTL_REALTIME));
        cacheConfigs.put("signalMarketData", defaultConfig.entryTtl(TTL_REALTIME));

        // 热点数据（5分钟）：龙虎榜、热点题材、北向资金
        cacheConfigs.put("signalHotData", defaultConfig.entryTtl(TTL_HOT));
        cacheConfigs.put("signalDragonTiger", defaultConfig.entryTtl(TTL_HOT));

        // 标准数据（15分钟）：股票列表、行业数据、概念板块
        cacheConfigs.put("signalReferenceData", defaultConfig.entryTtl(TTL_STANDARD));
        cacheConfigs.put("stockList", defaultConfig.entryTtl(TTL_STANDARD));
        cacheConfigs.put("stockDaily", defaultConfig.entryTtl(TTL_STANDARD));

        // 信息类数据（30分钟）：研报、公告、新闻
        cacheConfigs.put("infoReport", defaultConfig.entryTtl(TTL_INFO));
        cacheConfigs.put("infoNews", defaultConfig.entryTtl(TTL_INFO));
        cacheConfigs.put("infoFiling", defaultConfig.entryTtl(TTL_INFO));

        // fund 净值（60分钟）
        cacheConfigs.put("fundNav", defaultConfig.entryTtl(TTL_FUND));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(defaultConfig)
                .withInitialCacheConfigurations(cacheConfigs)
                .build();
    }
}
