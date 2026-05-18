package com.stock.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.stock.dto.ApiResponse;
import com.stock.entity.*;
import com.stock.mapper.StockDailyMapper;
import com.stock.service.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 行情层统一控制器 — 替代原有的 StockController
 *
 * 新架构:
 *   data-collector → Kafka → Spark Streaming → MySQL(stock/stock_daily)
 *   前端从此 API 读取，与采集层完全解耦
 *
 * 路由前缀: /api/market
 */
@RestController
@RequestMapping("/api/market")
public class MarketController {

    @Autowired
    private StockService stockService;

    @Autowired
    private StockDailyService stockDailyService;

    @Autowired
    private StockDailyMapper stockDailyMapper;

    // ==================== 股票列表 ====================

    @GetMapping("/list")
    public ApiResponse list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String industry,
            @RequestParam(required = false) String sortField,
            @RequestParam(required = false) String sortOrder) {

        int offset = (page - 1) * size;
        List<Map<String, Object>> records = stockDailyMapper.selectStocksWithPrice(
                keyword, industry, size, offset, sortField, sortOrder);

        LambdaQueryWrapper<Stock> countWrapper = new LambdaQueryWrapper<>();
        if (keyword != null) {
            countWrapper.like(Stock::getStockName, keyword)
                   .or().like(Stock::getStockCode, keyword);
        }
        if (industry != null) {
            countWrapper.eq(Stock::getIndustry, industry);
        }
        long total = stockService.count(countWrapper);

        return ApiResponse.page(records, total, page, size);
    }

    @GetMapping("/search")
    public ApiResponse search(@RequestParam String keyword,
                              @RequestParam(defaultValue = "10") int size) {
        LambdaQueryWrapper<Stock> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(Stock::getStockName, keyword)
               .or().like(Stock::getStockCode, keyword)
               .last("LIMIT " + size);
        List<Stock> list = stockService.list(wrapper);
        return ApiResponse.ok(list);
    }

    @GetMapping("/industries")
    public ApiResponse getIndustries() {
        List<Stock> all = stockService.list();
        List<String> industries = all.stream()
                .map(Stock::getIndustry)
                .filter(j -> j != null && !j.isEmpty())
                .distinct()
                .sorted()
                .collect(Collectors.toList());
        return ApiResponse.ok(industries);
    }

    @GetMapping("/{code}")
    public ApiResponse getByCode(@PathVariable String code) {
        LambdaQueryWrapper<Stock> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Stock::getStockCode, code);
        Stock stock = stockService.getOne(wrapper);
        if (stock == null) {
            return ApiResponse.notFound("股票不存在: " + code);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("stockCode", stock.getStockCode());
        result.put("stockName", stock.getStockName());
        result.put("market", stock.getMarket());
        result.put("industry", stock.getIndustry());
        result.put("listingDate", stock.getListingDate());
        result.put("pe", stock.getPe());
        result.put("pb", stock.getPb());
        result.put("totalMarketCap", stock.getTotalMarketCap());
        result.put("floatMarketCap", stock.getFloatMarketCap());

        List<StockDaily> latest = stockDailyService.getLatestDays(code, 1);
        if (!latest.isEmpty()) {
            StockDaily d = latest.get(0);
            result.put("price", d.getClosePrice());
            result.put("changePercent", d.getChangePercent());
            result.put("open", d.getOpenPrice());
            result.put("high", d.getHighPrice());
            result.put("low", d.getLowPrice());
            result.put("preClose", d.getPreClose());
            result.put("volume", d.getVolume());
            result.put("amount", d.getAmount());
            result.put("turnoverRate", d.getTurnoverRate());
            result.put("tradeDate", d.getTradeDate());
        }

        return ApiResponse.ok(result);
    }

    @GetMapping("/kline/{code}")
    public ApiResponse kline(@PathVariable String code,
                             @RequestParam(defaultValue = "60") int days) {
        return ApiResponse.ok(stockDailyService.getLatestDays(code, days));
    }

    @GetMapping("/kline/range")
    public ApiResponse klineRange(
            @RequestParam String code,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "60") int size) {
        LocalDate start = startDate != null ? LocalDate.parse(startDate) : null;
        LocalDate end = endDate != null ? LocalDate.parse(endDate) : null;
        return ApiResponse.ok(stockDailyService.getKLineData(code, start, end, page, size));
    }

    @GetMapping("/sector-ranking")
    public ApiResponse getSectorRanking(@RequestParam(required = false) String tradeDate) {
        String date = (tradeDate != null) ? tradeDate : stockDailyMapper.selectMaxTradeDate();
        if (date == null) {
            return ApiResponse.error("暂无数据");
        }
        return ApiResponse.ok(Map.of(
                "tradeDate", date,
                "records", stockDailyMapper.selectSectorRanking(date)
        ));
    }

    @GetMapping("/filter")
    public ApiResponse filter(
            @RequestParam(required = false) String industry,
            @RequestParam(required = false) BigDecimal minPrice,
            @RequestParam(required = false) BigDecimal maxPrice,
            @RequestParam(required = false) BigDecimal minChange,
            @RequestParam(defaultValue = "20") int limit) {
        return ApiResponse.ok(stockDailyMapper.selectStocksByFilter(
                industry, minPrice, maxPrice, minChange, limit));
    }

    @GetMapping("/max-date")
    public ApiResponse getMaxTradeDate() {
        String date = stockDailyMapper.selectMaxTradeDate();
        return ApiResponse.ok(Map.of("tradeDate", date));
    }
}
