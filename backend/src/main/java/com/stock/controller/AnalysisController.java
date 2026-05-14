package com.stock.controller;

import com.stock.entity.AnalysisResult;
import com.stock.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    @Autowired
    private AnalysisService analysisService;

    // ============================================================
    // 基础 CRUD（保存分析结果）
    // ============================================================

    @GetMapping("/{assetCode}")
    public ResponseEntity<List<AnalysisResult>> getAnalysis(
            @PathVariable String assetCode,
            @RequestParam(required = false) String type) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<AnalysisResult> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(AnalysisResult::getAssetCode, assetCode);
        if (type != null) {
            wrapper.eq(AnalysisResult::getAnalysisType, type);
        }
        wrapper.orderByDesc(AnalysisResult::getAnalysisDate);
        return ResponseEntity.ok(analysisService.list(wrapper));
    }

    @PostMapping("/save")
    public ResponseEntity<Boolean> saveAnalysis(@RequestBody AnalysisResult result) {
        return ResponseEntity.ok(analysisService.save(result));
    }

    // ============================================================
    // 收益率
    // ============================================================

    /** 年收益率 */
    @GetMapping("/{stockCode}/yearly-return")
    public ResponseEntity<List<Map<String, Object>>> getYearlyReturn(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "3") int years) {
        return ResponseEntity.ok(analysisService.getYearlyReturn(stockCode, years));
    }

    /** 月收益率 */
    @GetMapping("/{stockCode}/monthly-return")
    public ResponseEntity<List<Map<String, Object>>> getMonthlyReturn(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "12") int months) {
        return ResponseEntity.ok(analysisService.getMonthlyReturn(stockCode, months));
    }

    // ============================================================
    // 趋势
    // ============================================================

    /** 趋势分析 */
    @GetMapping("/{stockCode}/trend")
    public ResponseEntity<Map<String, Object>> getTrend(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(analysisService.getTrendAnalysis(stockCode, days));
    }

    // ============================================================
    // 筛选
    // ============================================================

    /** 综合筛选 */
    @PostMapping("/filter")
    public ResponseEntity<List<Map<String, Object>>> filterStocks(
            @RequestBody Map<String, Object> conditions) {
        return ResponseEntity.ok(analysisService.filterStocks(conditions));
    }

    // ============================================================
    // 相关性
    // ============================================================

    /** 相关性分析 */
    @GetMapping("/correlation")
    public ResponseEntity<Map<String, Object>> getCorrelation(
            @RequestParam String codeA,
            @RequestParam String codeB,
            @RequestParam(defaultValue = "60") int days) {
        Map<String, Object> result = Map.of(
                "codeA", codeA,
                "codeB", codeB,
                "correlation", analysisService.getCorrelation(codeA, codeB, days)
        );
        return ResponseEntity.ok(result);
    }

    // ============================================================
    // 行业排行
    // ============================================================

    /** 行业涨跌排行 */
    @GetMapping("/sector-ranking")
    public ResponseEntity<List<Map<String, Object>>> getSectorRanking(
            @RequestParam(required = false) String tradeDate) {
        return ResponseEntity.ok(analysisService.getSectorRanking(tradeDate));
    }
}
