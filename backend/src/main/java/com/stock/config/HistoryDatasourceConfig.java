package com.stock.config;

import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;

/**
 * 数据源配置（主库 stock_analysis + 历史库 stock_history）
 *
 * 坑：@ConditionalOnMissingBean(DataSource.class) 会导致 Spring Boot
 * 当存在任何 DataSource bean 时跳过自动配置，因此必须在此处显式声明 @Primary 主数据源。
 * 且必须使用 DataSourceProperties 构建（确保 url -> jdbcUrl 映射正确）。
 */
@Configuration
public class HistoryDatasourceConfig {

    /**
     * 主数据源 — stock_analysis（MyBatis 默认使用 @Primary）
     * 使用 DataSourceProperties 确保 url 被正确映射到 HikariCP 的 jdbcUrl
     */
    @Bean
    @Primary
    @ConfigurationProperties(prefix = "spring.datasource")
    public DataSourceProperties primaryDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean
    @Primary
    public DataSource primaryDataSource(DataSourceProperties properties) {
        return properties.initializeDataSourceBuilder().build();
    }

    /**
     * 历史数据源 — stock_history（仅 HistoryController / Redis 降级使用）
     */
    @Bean
    @ConfigurationProperties(prefix = "history.datasource")
    public DataSource historyDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    public JdbcTemplate historyJdbcTemplate() {
        return new JdbcTemplate(historyDataSource());
    }
}
