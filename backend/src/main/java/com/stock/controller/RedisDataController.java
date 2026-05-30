package com.stock.controller;

import com.stock.service.RedisReader;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * Redis 数据控制器 — 所有市场数据通过此控制器从 Redis 读取
 *
 * 数据链路: 采集器→CSV→HDFS→Hive→Python管道(每60s)→Redis
 * MySQL 仅存业务数据 (user/watchlist)
 */
@RestController
@RequestMapping("/api/v2")
public class RedisDataController {

    @Autowired
    private RedisReader redisReader;

    // ========== 行情层 /market ==========

    @GetMapping("/market/list")
    public Map<String, Object> marketList(@RequestParam(defaultValue = "1") int page,
                                          @RequestParam(defaultValue = "20") int size) {
        return pageResult(redisReader.getAsList("market:stock_basic"), page, size);
    }

    @GetMapping("/market/industries")
    public List<Map<String, Object>> industries() {
        return redisReader.getAsList("market:industries");
    }

    @GetMapping("/market/sector-ranking")
    public List<Map<String, Object>> sectorRanking() {
        return redisReader.getAsList("market:sector_ranking");
    }

    @GetMapping("/market/max-date")
    public Map<String, Object> maxDate() {
        List<Map<String, Object>> list = redisReader.getAsList("market:max_date");
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("tradeDate", list.isEmpty() ? "2026-05-29" : list.get(0).get("trade_date"));
        return r;
    }

    // ========== 指数 /index ==========

    @GetMapping("/index/list")
    public List<Map<String, Object>> indexList() {
        return redisReader.getAsList("market:index_list");
    }

    @GetMapping("/index/{code}")
    public Map<String, Object> indexInfo(@PathVariable String code) {
        List<Map<String, Object>> list = redisReader.getAsList("market:index_list");
        return list.stream().filter(m -> code.equals(m.get("index_code"))).findFirst()
            .orElse(Map.of("indexCode", code, "note", "数据加载中"));
    }

    @GetMapping("/index/{code}/kline")
    public List<Map<String, Object>> indexKline(@PathVariable String code,
                                                 @RequestParam(defaultValue = "60") int days) {
        return redisReader.getAsList("market:index_kline_" + code);
    }

    // ========== 信号层 /signal ==========

    @GetMapping("/signal/northbound/latest")
    public List<Map<String, Object>> northbound(@RequestParam(defaultValue = "10") int days) {
        return redisReader.getAsList("market:northbound");
    }

    @GetMapping("/signal/hot-reason")
    public List<Map<String, Object>> hotReason() {
        return redisReader.getAsList("market:hot_reason");
    }

    @GetMapping("/signal/industry-compare")
    public List<Map<String, Object>> industryCompare() {
        return redisReader.getAsList("market:industry_compare");
    }

    @GetMapping("/signal/dragon-tiger/daily")
    public List<Map<String, Object>> dragonTiger() {
        return redisReader.getAsList("market:dragon_tiger");
    }

    @GetMapping("/signal/fund-flow/{code}")
    public List<Map<String, Object>> fundFlow(@PathVariable String code) {
        return redisReader.getAsList("market:fund_flow_" + code);
    }

    @GetMapping("/signal/lockup/upcoming")
    public List<Map<String, Object>> lockupUpcoming() {
        return redisReader.getAsList("market:lockup_upcoming");
    }

    // ========== 资讯层 /info ==========

    @GetMapping("/info/cls-news")
    public List<Map<String, Object>> clsNews(@RequestParam(defaultValue = "20") int limit) {
        List<Map<String, Object>> all = redisReader.getAsList("market:cls_news");
        return all.subList(0, Math.min(limit, all.size()));
    }

    @GetMapping("/info/global-news")
    public List<Map<String, Object>> globalNews(@RequestParam(defaultValue = "10") int limit) {
        List<Map<String, Object>> all = redisReader.getAsList("market:global_news");
        return all.subList(0, Math.min(limit, all.size()));
    }

    // ========== 基金 /fund ==========

    @GetMapping("/fund/list")
    public Map<String, Object> fundList(@RequestParam(defaultValue = "1") int page,
                                        @RequestParam(defaultValue = "20") int size) {
        return pageResult(redisReader.getAsList("market:fund_list"), page, size);
    }

    @GetMapping("/fund/{code}/nav")
    public List<Map<String, Object>> fundNav(@PathVariable String code,
                                              @RequestParam(defaultValue = "30") int days) {
        return redisReader.getAsList("market:fund_nav");
    }

    // ========== 健康检查 ==========

    @GetMapping("/ping")
    public Map<String, Object> ping() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.put("redis_keys", List.of("market:stock_basic", "market:cls_news",
            "market:northbound", "market:fund_nav"));
        result.put("data_source", "Hive→Redis pipeline (每60s)");
        return result;
    }

    // ========== 工具 ==========

    private Map<String, Object> pageResult(List<Map<String, Object>> all, int page, int size) {
        int from = (page - 1) * size;
        int to = Math.min(from + size, all.size());
        List<Map<String, Object>> records = from < all.size() ? all.subList(from, to) : Collections.emptyList();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("records", records);
        result.put("total", all.size());
        result.put("page", page);
        result.put("size", size);
        result.put("totalPages", (int) Math.ceil((double) all.size() / size));
        return result;
    }
}
