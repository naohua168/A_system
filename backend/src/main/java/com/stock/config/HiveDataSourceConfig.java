package com.stock.config;

/**
 * Hive 数据源配置（预留 — 数据通过 Python Hive→Redis 管道写入，后端直接读 Redis）
 * 不再通过 Spring 管理，所有市场数据查询走 RedisCacheService。
 */
public class HiveDataSourceConfig {
}
