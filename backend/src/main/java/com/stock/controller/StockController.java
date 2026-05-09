package com.stock.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.stock.entity.Stock;
import com.stock.entity.StockDaily;
import com.stock.mapper.StockDailyMapper;
import com.stock.service.StockDailyService;
import com.stock.service.StockService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/stock")
public class StockController {

    @Autowired
    private StockService stockService;

    @Autowired
    private StockDailyService stockDailyService;

    @Autowired
    private StockDailyMapper stockDailyMapper;

    @GetMapping("/list")
    public ResponseEntity<?> list(@RequestParam(defaultValue = "1") int page,
                                   @RequestParam(defaultValue = "20") int size,
                                   @RequestParam(required = false) String keyword,
                                   @RequestParam(required = false) String industry) {
        int offset = (page - 1) * size;
        List<Map<String, Object>> records = stockDailyMapper.selectStocksWithPrice(keyword, industry, size, offset);
        LambdaQueryWrapper<Stock> countWrapper = new LambdaQueryWrapper<>();
        if (keyword != null) {
            countWrapper.like(Stock::getStockName, keyword)
                   .or().like(Stock::getStockCode, keyword);
        }
        if (industry != null) {
            countWrapper.eq(Stock::getIndustry, industry);
        }
        long total = stockService.count(countWrapper);
        return ResponseEntity.ok(Map.of(
                "records", records,
                "total", total,
                "page", page,
                "size", size
        ));
    }

    @GetMapping("/search")
    public ResponseEntity<?> search(@RequestParam String keyword,
                                     @RequestParam(defaultValue = "10") int size) {
        LambdaQueryWrapper<Stock> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(Stock::getStockName, keyword)
               .or().like(Stock::getStockCode, keyword)
               .last("LIMIT " + size);
        List<Stock> list = stockService.list(wrapper);
        return ResponseEntity.ok(list);
    }

    @GetMapping("/industries")
    public ResponseEntity<List<String>> getIndustries() {
        List<Stock> all = stockService.list();
        List<String> industries = all.stream()
                .map(Stock::getIndustry)
                .filter(j -> j != null && !j.isEmpty())
                .distinct()
                .sorted()
                .collect(Collectors.toList());
        return ResponseEntity.ok(industries);
    }

    @GetMapping("/{code}")
    public ResponseEntity<?> getByCode(@PathVariable String code) {
        LambdaQueryWrapper<Stock> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Stock::getStockCode, code);
        Stock stock = stockService.getOne(wrapper);
        if (stock == null) {
            return ResponseEntity.status(404).body(Map.of("error", "股票不存在"));
        }
        return ResponseEntity.ok(stock);
    }

    @GetMapping("/kline/{code}")
    public ResponseEntity<List<StockDaily>> kline(@PathVariable String code,
                                                   @RequestParam(defaultValue = "60") int days) {
        return ResponseEntity.ok(stockDailyService.getLatestDays(code, days));
    }
}
