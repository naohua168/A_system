package com.stock.controller;

import com.stock.dto.ApiResponse;
import com.stock.entity.AnalysisResult;
import com.stock.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 分析层控制器 — 技术指标 + 缠论 + 量化策略 + 排名筛选
 *
 * 新架构:
 *   本地: analysis-algorithms/analysis_orchestrator.py (Pandas 计算)
 *   预计算: Spark Streaming → MySQL precomputed_* 表
 *   后端: 优先读预计算结果，无则提示
 *
 * 路由前缀: /api/analysis
 */
@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    @Autowired
    private AnalysisService analysisService;

    // ==================== 分析结果 CRUD ====================

    @GetMapping("/{assetCode}")
    public ApiResponse getAnalysis(
            @PathVariable String assetCode,
            @RequestParam(required = false) String type) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<AnalysisResult> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(AnalysisResult::getAssetCode, assetCode);
        if (type != null) {
            wrapper.eq(AnalysisResult::getAnalysisType, type);
        }
        wrapper.orderByDesc(AnalysisResult::getAnalysisDate);
        List<AnalysisResult> list = analysisService.list(wrapper);
        return ApiResponse.ok(list);
    }

    @PostMapping("/save")
    public ApiResponse saveAnalysis(@RequestBody AnalysisResult result) {
        boolean saved = analysisService.save(result);
        return saved ? ApiResponse.created(result) : ApiResponse.error("保存失败");
    }

    // ==================== 收益率 ====================

    @GetMapping("/{stockCode}/yearly-return")
    public ApiResponse getYearlyReturn(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "3") int years) {
        return ApiResponse.ok(analysisService.getYearlyReturn(stockCode, years));
    }

    @GetMapping("/{stockCode}/monthly-return")
    public ApiResponse getMonthlyReturn(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "12") int months) {
        return ApiResponse.ok(analysisService.getMonthlyReturn(stockCode, months));
    }

    // ==================== 趋势分析 ====================

    @GetMapping("/{stockCode}/trend")
    public ApiResponse getTrend(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "30") int days) {
        // 修复: 增加 null 判断，避免 trend.isEmpty() 触发 NullPointerException
        Map<String, Object> trend = analysisService.getTrendAnalysis(stockCode, days);
        if (trend == null || trend.isEmpty()) {
            return ApiResponse.error("无数据");
        }
        return ApiResponse.ok(trend);
    }

    // ==================== 筛选 ====================

    @PostMapping("/filter")
    public ApiResponse filterStocks(@RequestBody Map<String, Object> conditions) {
        List<Map<String, Object>> result = analysisService.filterStocks(conditions);
        return ApiResponse.ok(result);
    }

    // ==================== 相关性 ====================

    @GetMapping("/correlation")
    public ApiResponse getCorrelation(
            @RequestParam String codeA,
            @RequestParam String codeB,
            @RequestParam(defaultValue = "60") int days) {
        return ApiResponse.ok(Map.of(
                "codeA", codeA,
                "codeB", codeB,
                "correlation", analysisService.getCorrelation(codeA, codeB, days)
        ));
    }

    // ==================== 行业排行 ====================

    @GetMapping("/sector-ranking")
    public ApiResponse getSectorRanking(@RequestParam(required = false) String tradeDate) {
        return ApiResponse.ok(analysisService.getSectorRanking(tradeDate));
    }
}
