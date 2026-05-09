package com.stock.controller;

import com.stock.entity.MarketIndex;
import com.stock.entity.IndexDaily;
import com.stock.service.IndexService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/index")
public class IndexController {

    private final IndexService indexService;

    public IndexController(IndexService indexService) {
        this.indexService = indexService;
    }

    /** 获取所有指数列表（带最新行情） */
    @GetMapping("/list")
    public ResponseEntity<List<Map<String, Object>>> getIndexList() {
        return ResponseEntity.ok(indexService.getIndexList());
    }

    /** 获取指数基本信息 */
    @GetMapping("/{code}")
    public ResponseEntity<MarketIndex> getIndexInfo(@PathVariable("code") String code) {
        MarketIndex info = indexService.getIndexInfo(code);
        return info != null ? ResponseEntity.ok(info) : ResponseEntity.notFound().build();
    }

    /** 获取指数K线数据 */
    @GetMapping("/{code}/kline")
    public ResponseEntity<List<IndexDaily>> getKlineData(
            @PathVariable("code") String code,
            @RequestParam(value = "days", defaultValue = "120") int days) {
        return ResponseEntity.ok(indexService.getKlineData(code, days));
    }

    /** 获取最近交易日 */
    @GetMapping("/max-date")
    public ResponseEntity<Map<String, String>> getMaxTradeDate() {
        String date = indexService.getMaxTradeDate();
        return ResponseEntity.ok(Map.of("tradeDate", date != null ? date : ""));
    }
}
