package com.stock.controller;

import com.stock.service.RedisReader;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

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

    // ========================================================================
    // 行情层 /market
    // ========================================================================

    @GetMapping("/market/list")
    public Map<String, Object> marketList(@RequestParam(defaultValue = "1") int page,
                                          @RequestParam(defaultValue = "20") int size) {
        List<Map<String, Object>> all = redisReader.getAsList("market:stock_basic");
        // stock_basic 已含 changePct/price（由 auto_seed.py 从 CSV 写入），无需额外 enrich
        return pageResult(all, page, size);
    }

    @GetMapping("/market/detail/{code}")
    public Map<String, Object> marketDetail(@PathVariable String code) {
        List<Map<String, Object>> list = redisReader.getAsList("market:stock_basic");
        // 遍历查找 — 避免 stream filter 的 Jackson 类型推断问题
        for (Map<String, Object> m : list) {
            Object sc = m.get("stockCode");
            if (sc != null) {
                String scStr = sc.toString();
                if (code.equals(scStr)) return m;
            }
            Object sc2 = m.get("stock_code");
            if (sc2 != null && code.equals(sc2.toString())) return m;
        }
        return Map.of("stockCode", code, "stockName", "数据加载中");
    }

    @GetMapping("/market/kline/{code}")
    public List<Map<String, Object>> marketKline(@PathVariable String code,
                                                  @RequestParam(defaultValue = "60") int days,
                                                  @RequestParam(defaultValue = "day") String period) {
        return getPeriodKline("market:kline", code, days, period);
    }

    @GetMapping("/market/kline/range")
    public List<Map<String, Object>> marketKlineRange(@RequestParam String code,
                                                       @RequestParam String startDate,
                                                       @RequestParam String endDate,
                                                       @RequestParam(defaultValue = "day") String period) {
        return getPeriodKline("market:kline", code, 365, period);
    }

    @GetMapping("/market/analysis/{type}")
    public List<Map<String, Object>> marketAnalysis(@PathVariable String type) {
        // Spark 批处理分析结果: top_gainers / top_losers / high_volume
        return redisReader.getAsList("market:analysis:" + type);
    }

    @GetMapping("/market/search")
    public List<Map<String, Object>> searchStocks(@RequestParam String keyword,
                                                   @RequestParam(defaultValue = "10") int size) {
        List<Map<String, Object>> all = redisReader.getAsList("market:stock_basic");
        String kw = keyword.toLowerCase();
        return all.stream()
            .filter(m -> {
                String code = m.get("stockCode") != null ? String.valueOf(m.get("stockCode")) : String.valueOf(m.getOrDefault("stock_code", ""));
                String name = m.get("stockName") != null ? String.valueOf(m.get("stockName")) : String.valueOf(m.getOrDefault("stock_name", ""));
                return code.contains(kw) || name.contains(kw);
            })
            .limit(size)
            .collect(Collectors.toList());
    }

    @GetMapping("/market/industries")
    public List<Map<String, Object>> industries() {
        return redisReader.getAsList("market:industries");
    }

    @GetMapping("/market/sector-ranking")
    public List<Map<String, Object>> sectorRanking(@RequestParam(required = false) String tradeDate) {
        // industry_compare 有真实的行业排行数据（industryName, changePct, upCount, downCount）
        // sector_ranking 是旧的 stock-level 数据，已废弃
        return redisReader.getAsList("market:industry_compare");
    }

    @GetMapping("/market/sector-kline")
    public List<Map<String, Object>> sectorKline(@RequestParam String industry,
                                                  @RequestParam(defaultValue = "60") int days) {
        return redisReader.getAsList("market:sector_kline_" + industry);
    }

    @GetMapping("/market/industry-treemap")
    public List<Map<String, Object>> industryTreemap(@RequestParam(required = false) String tradeDate) {
        return redisReader.getAsList("market:industry_treemap");
    }

    @GetMapping("/market/etf")
    public Map<String, Object> etfList(@RequestParam(defaultValue = "1") int page,
                                        @RequestParam(defaultValue = "20") int size) {
        return pageResult(redisReader.getAsList("market:etf_list"), page, size);
    }

    @GetMapping("/market/filter")
    public List<Map<String, Object>> filterStocks(@RequestParam Map<String, String> params) {
        // 暂不支持复杂过滤，返回全部股票列表
        return redisReader.getAsList("market:stock_basic");
    }

    @GetMapping("/market/markets")
    public List<Map<String, Object>> markets() {
        return redisReader.getAsList("market:market_list");
    }

    @GetMapping("/market/financial/{code}")
    public List<Map<String, Object>> financial(@PathVariable String code) {
        return redisReader.getAsList("market:financial_" + code);
    }

    @GetMapping("/market/max-date")
    public Map<String, Object> maxDate() {
        List<Map<String, Object>> list = redisReader.getAsList("market:max_date");
        Map<String, Object> r = new LinkedHashMap<>();
        if (!list.isEmpty()) {
            Object td = list.get(0).get("tradeDate");
            r.put("tradeDate", td != null ? td.toString() : "2026-06-01");
        } else {
            r.put("tradeDate", "2026-06-01");
        }
        return r;
    }

    // ========================================================================
    // 指数 /index
    // ========================================================================

    @GetMapping("/index/list")
    public List<Map<String, Object>> indexList() {
        return redisReader.getAsList("market:index_list");
    }

    @GetMapping("/index/{code}")
    public Map<String, Object> indexInfo(@PathVariable String code) {
        List<Map<String, Object>> list = redisReader.getAsList("market:index_list");
        return list.stream().filter(m -> code.equals(m.get("indexCode")) || code.equals(m.get("index_code"))).findFirst()
            .orElse(Map.of("indexCode", code, "note", "数据加载中"));
    }

    @GetMapping("/index/{code}/kline")
    public List<Map<String, Object>> indexKline(@PathVariable String code,
                                                 @RequestParam(defaultValue = "60") int days,
                                                 @RequestParam(defaultValue = "day") String period) {
        return getPeriodKline("market:index_kline", code, days, period);
    }

    /** 多周期 K 线：先查带周期的 key，不存在则从日K聚合 */
    private List<Map<String, Object>> getPeriodKline(String prefix, String code, int days, String period) {
        // 对 day 周期使用原有的 key 保持向后兼容
        if ("day".equals(period)) {
            return redisReader.getAsList(prefix + "_" + code);
        }
        // 先查 Redis 中是否有该周期的专用数据
        String periodKey = prefix + "_" + period + "_" + code;
        List<Map<String, Object>> cached = redisReader.getAsList(periodKey);
        if (cached != null && !cached.isEmpty()) {
            return cached;
        }
        // 无专用数据，从日K聚合
        List<Map<String, Object>> dayData = redisReader.getAsList(prefix + "_" + code);
        if (dayData == null || dayData.isEmpty()) return dayData;
        return aggregatePeriod(dayData, period, days);
    }

    /** 从日K数据聚合为周K/月K */
    private List<Map<String, Object>> aggregatePeriod(List<Map<String, Object>> dayData, String period, int maxDays) {
        // 数据是降序（最新在前），取 maxDays 天
        List<Map<String, Object>> limited = new ArrayList<>(dayData);
        // 周K/月K需要更多数据量才有意义
        int dataDays = maxDays;
        if ("week".equals(period) && dataDays < 120) dataDays = 120;
        if ("month".equals(period) && dataDays < 365) dataDays = 365;
        if (limited.size() > dataDays) limited = limited.subList(0, dataDays);
        // 翻转成升序以便分组
        java.util.Collections.reverse(limited);

        java.util.Map<String, List<Map<String, Object>>> groups = new java.util.TreeMap<>();
        java.time.format.DateTimeFormatter fmt = java.time.format.DateTimeFormatter.BASIC_ISO_DATE;
        java.time.temporal.WeekFields wf = java.time.temporal.WeekFields.ISO;

        // 分钟K线无专用数据时直接返回日K数据（无法从日K聚合出分钟级）
        if ("5min".equals(period) || "15min".equals(period) || "30min".equals(period) || "60min".equals(period)) {
            return dayData;
        }
        for (Map<String, Object> r : limited) {
            String td = r.getOrDefault("tradeDate", "").toString();
            if (td.length() < 8) continue;
            String key;
            try {
                java.time.LocalDate d = java.time.LocalDate.parse(td, fmt);
                if ("week".equals(period)) {
                    int y = d.get(wf.weekBasedYear());
                    int w = d.get(wf.weekOfWeekBasedYear());
                    key = String.format("%04d%02d", y, w);
                } else {
                    key = td.substring(0, 6);
                }
            } catch (Exception ignored) { continue; }
            groups.computeIfAbsent(key, k -> new ArrayList<>()).add(r);
        }

        List<Map<String, Object>> result = new ArrayList<>();
        for (List<Map<String, Object>> g : groups.values()) {
            if (g.isEmpty()) continue;
            Map<String, Object> first = g.get(0);
            Map<String, Object> last = g.get(g.size() - 1);
            Map<String, Object> agg = new HashMap<>(first);
            agg.put("openPoint", first.get("openPoint"));
            agg.put("closePoint", last.get("closePoint") != null ? last.get("closePoint")
                : (last.get("closePrice") != null ? last.get("closePrice") : last.get("closePoint")));
            double high = 0, low = Double.MAX_VALUE;
            long vol = 0;
            for (Map<String, Object> r : g) {
                high = Math.max(high, safeDouble(r.getOrDefault("highPoint", r.getOrDefault("highPrice", 0))));
                low = Math.min(low, safeDouble(r.getOrDefault("lowPoint", r.getOrDefault("lowPrice", Double.MAX_VALUE))));
                vol += safeLong(r.getOrDefault("volume", 0));
            }
            agg.put("highPoint", high);
            agg.put("lowPoint", low < Double.MAX_VALUE ? low : first.get("lowPoint"));
            agg.put("volume", vol);
            agg.put("amount", last.get("amount"));
            result.add(agg);
        }
        java.util.Collections.reverse(result); // 恢复降序
        return result;
    }

    private double safeDouble(Object v) {
        try { return ((Number) v).doubleValue(); } catch (Exception e) { return 0; }
    }
    private long safeLong(Object v) {
        try { return ((Number) v).longValue(); } catch (Exception e) { return 0; }
    }

    @GetMapping("/index/max-date")
    public Map<String, Object> indexMaxDate() {
        return maxDate();
    }

    // ========================================================================
    // 信号层 /signal
    // ========================================================================

    @GetMapping("/signal/northbound/latest")
    public List<Map<String, Object>> northbound(@RequestParam(defaultValue = "10") int days) {
        return redisReader.getAsList("market:northbound");
    }

    @GetMapping("/signal/hot-reason")
    public List<Map<String, Object>> hotReason(@RequestParam(required = false) String date) {
        return redisReader.getAsList("market:hot_reason");
    }

    @GetMapping("/signal/industry-compare")
    public List<Map<String, Object>> industryCompare(@RequestParam(required = false) String date) {
        return redisReader.getAsList("market:industry_compare");
    }

    @GetMapping("/signal/dragon-tiger/daily")
    public List<Map<String, Object>> dragonTigerDaily(@RequestParam(required = false) String date) {
        return redisReader.getAsList("market:dragon_tiger");
    }

    @GetMapping("/signal/dragon-tiger/stock/{code}")
    public List<Map<String, Object>> dragonTigerByStock(@PathVariable String code) {
        return redisReader.getAsList("market:dragon_tiger_" + code);
    }

    @GetMapping("/signal/fund-flow/{code}")
    public List<Map<String, Object>> fundFlow(@PathVariable String code,
                                               @RequestParam(defaultValue = "20") int limit) {
        return redisReader.getAsList("market:fund_flow_" + code);
    }

    @GetMapping("/signal/concept-blocks/{code}")
    public List<Map<String, Object>> conceptBlocks(@PathVariable String code) {
        return redisReader.getAsList("market:concept_blocks_" + code);
    }

    @GetMapping("/signal/lockup/upcoming")
    public List<Map<String, Object>> lockupUpcoming() {
        return redisReader.getAsList("market:lockup_upcoming");
    }

    @GetMapping("/signal/lockup/stock/{code}")
    public List<Map<String, Object>> lockupByStock(@PathVariable String code) {
        return redisReader.getAsList("market:lockup_" + code);
    }

    // ========================================================================
    // 资讯层 /info
    // ========================================================================

    @GetMapping("/info/cls-news")
    public List<Map<String, Object>> clsNews(@RequestParam(defaultValue = "20") int limit,
                                              @RequestParam(required = false) String since) {
        List<Map<String, Object>> all = redisReader.getAsList("market:cls_news");
        return all.subList(0, Math.min(limit, all.size()));
    }

    @GetMapping("/info/global-news")
    public List<Map<String, Object>> globalNews(@RequestParam(defaultValue = "10") int limit) {
        List<Map<String, Object>> all = redisReader.getAsList("market:global_news");
        return all.subList(0, Math.min(limit, all.size()));
    }

    @GetMapping("/info/research/{code}")
    public List<Map<String, Object>> researchReports(@PathVariable String code) {
        return redisReader.getAsList("market:research_" + code);
    }

    @GetMapping("/info/research/range")
    public List<Map<String, Object>> researchByDateRange(@RequestParam String code,
                                                          @RequestParam(required = false) String startDate,
                                                          @RequestParam(required = false) String endDate) {
        return redisReader.getAsList("market:research_" + code);
    }

    @GetMapping("/info/consensus-eps/{code}")
    public List<Map<String, Object>> consensusEps(@PathVariable String code) {
        return redisReader.getAsList("market:consensus_eps_" + code);
    }

    @GetMapping("/info/news/{code}")
    public List<Map<String, Object>> stockNews(@PathVariable String code,
                                                @RequestParam(defaultValue = "30") int days) {
        return redisReader.getAsList("market:news_" + code);
    }

    @GetMapping("/info/filings/{code}")
    public Map<String, Object> filings(@PathVariable String code,
                                        @RequestParam(defaultValue = "1") int page,
                                        @RequestParam(defaultValue = "20") int size) {
        return pageResult(redisReader.getAsList("market:filings_" + code), page, size);
    }

    // ========================================================================
    // 基金 /fund
    // ========================================================================

    @GetMapping("/fund/list")
    public Map<String, Object> fundList(@RequestParam(defaultValue = "1") int page,
                                        @RequestParam(defaultValue = "20") int size) {
        return pageResult(redisReader.getAsList("market:fund_list"), page, size);
    }

    @GetMapping("/fund/{code}")
    public Map<String, Object> fundInfo(@PathVariable String code) {
        List<Map<String, Object>> list = redisReader.getAsList("market:fund_list");
        return list.stream().filter(m -> code.equals(m.get("fundCode")) || code.equals(m.get("fund_code"))).findFirst()
            .orElse(Map.of("fundCode", code, "note", "数据加载中"));
    }

    @GetMapping("/fund/{code}/nav")
    public List<Map<String, Object>> fundNav(@PathVariable String code,
                                              @RequestParam(defaultValue = "30") int days) {
        return redisReader.getAsList("market:fund_nav");
    }

    @GetMapping("/fund/{code}/holdings")
    public List<Map<String, Object>> fundHoldings(@PathVariable String code) {
        return redisReader.getAsList("market:fund_holdings_" + code);
    }

    // ========================================================================
    // 健康检查
    // ========================================================================

    @GetMapping("/ping")
    public Map<String, Object> ping() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.put("redis_keys", List.of("market:stock_basic", "market:cls_news",
            "market:northbound", "market:fund_nav", "market:global_news",
            "market:hot_reason", "market:fund_list"));
        result.put("data_source", "Hive→Redis pipeline (每60s)");
        return result;
    }

    // ========================================================================
    // 工具方法
    // ========================================================================

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
