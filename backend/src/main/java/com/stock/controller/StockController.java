package com.stock.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.stock.entity.Stock;
import com.stock.entity.StockDaily;
import com.stock.service.StockDailyService;
import com.stock.service.StockService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/stock")
public class StockController {

    @Autowired
    private StockService stockService;

    @Autowired
    private StockDailyService stockDailyService;

    @GetMapping("/list")
    public ResponseEntity<IPage<Stock>> list(@RequestParam(defaultValue = "1") int page,
                                              @RequestParam(defaultValue = "20") int size,
                                              @RequestParam(required = false) String keyword,
                                              @RequestParam(required = false) String industry) {
        LambdaQueryWrapper<Stock> wrapper = new LambdaQueryWrapper<>();
        if (keyword != null) {
            wrapper.like(Stock::getStockName, keyword)
                   .or().like(Stock::getStockCode, keyword);
        }
        if (industry != null) {
            wrapper.eq(Stock::getIndustry, industry);
        }
        return ResponseEntity.ok(stockService.page(new Page<>(page, size), wrapper));
    }

    @GetMapping("/{code}")
    public ResponseEntity<Stock> getByCode(@PathVariable String code) {
        LambdaQueryWrapper<Stock> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Stock::getStockCode, code);
        return ResponseEntity.ok(stockService.getOne(wrapper));
    }

    @GetMapping("/kline/{code}")
    public ResponseEntity<List<StockDaily>> kline(@PathVariable String code,
                                                   @RequestParam(defaultValue = "60") int days) {
        return ResponseEntity.ok(stockDailyService.getLatestDays(code, days));
    }
}
