package com.stock.controller;

import com.stock.service.RedisReader;
import com.stock.dto.ApiResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * 历史数据查询控制器
 * 当日数据 → Redis；历史数据 → MySQL stock_history
 * Redis 不可用时自动降级 MySQL 兜底
 */
@RestController
@RequestMapping("/api/v2/history")
public class HistoryController {

    private static final Logger log = LoggerFactory.getLogger(HistoryController.class);
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    @Autowired
    private RedisReader redisReader;

    @Autowired(required = false)
    @Qualifier("historyJdbcTemplate")
    private JdbcTemplate historyJdbc;

    private String today() {
        return LocalDate.now().format(FMT);
    }

    private boolean isToday(String date) {
        return date == null || date.isEmpty() || date.equals(today());
    }

    private List<Map<String, Object>> queryOrFallback(String redisKey, String table, String date) {
        if (isToday(date)) {
            return redisReader.getAsList(redisKey);
        }
        return queryMysql(table, date);
    }

    private List<Map<String, Object>> queryMysql(String table, String date) {
        if (historyJdbc == null) return List.of();
        try {
            String sql = "SELECT * FROM " + table + " WHERE trade_date = ? ORDER BY trade_date DESC LIMIT 1000";
            return historyJdbc.queryForList(sql, date);
        } catch (DataAccessException e) {
            log.warn("History {} 查询失败: {}", table, e.getMessage());
            return List.of();
        }
    }

    @GetMapping("/kline/{code}")
    public ApiResponse getKline(@PathVariable String code,
                                @RequestParam(defaultValue = "") String date) {
        if (isToday(date)) {
            return ApiResponse.ok(redisReader.getAsList("market:kline_" + code));
        }
        return ApiResponse.ok(queryMysql("stock_daily", date));
    }

    @GetMapping("/index/list")
    public ApiResponse getIndexList(@RequestParam(defaultValue = "") String date) {
        return ApiResponse.ok(queryOrFallback("market:index_list", "index_daily", date));
    }

    @GetMapping("/market/list")
    public ApiResponse getMarketList(@RequestParam(defaultValue = "") String date) {
        return ApiResponse.ok(queryOrFallback("market:stock_basic", "stock_daily", date));
    }

    @GetMapping("/industry-compare")
    public ApiResponse getIndustryCompare(@RequestParam(defaultValue = "") String date) {
        return ApiResponse.ok(queryOrFallback("market:industry_compare", "industry_daily", date));
    }

    @GetMapping("/northbound")
    public ApiResponse getNorthbound(@RequestParam(defaultValue = "") String date) {
        return ApiResponse.ok(queryOrFallback("market:northbound", "northbound_daily", date));
    }

    @GetMapping("/hot-reason")
    public ApiResponse getHotReason(@RequestParam(defaultValue = "") String date) {
        return ApiResponse.ok(queryOrFallback("market:hot_reason", "hot_reason_daily", date));
    }

    @GetMapping("/dragon-tiger")
    public ApiResponse getDragonTiger(@RequestParam(defaultValue = "") String date) {
        return ApiResponse.ok(queryOrFallback("market:dragon_tiger", "dragon_tiger_daily", date));
    }

    @GetMapping("/news")
    public ApiResponse getNews(@RequestParam(defaultValue = "") String date,
                               @RequestParam(defaultValue = "cls") String source) {
        if (isToday(date)) {
            return ApiResponse.ok(redisReader.getAsList("market:" + source + "_news"));
        }
        if (historyJdbc == null) return ApiResponse.ok(List.of());
        try {
            String sql = "SELECT * FROM info_news WHERE source = ? AND DATE(publish_time) = ? ORDER BY publish_time DESC LIMIT 200";
            return ApiResponse.ok(historyJdbc.queryForList(sql, source, date));
        } catch (DataAccessException e) {
            return ApiResponse.ok(List.of());
        }
    }
}
