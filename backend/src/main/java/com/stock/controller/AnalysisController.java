package com.stock.controller;

import com.stock.dto.ApiResponse;
import com.stock.entity.AnalysisResult;
import com.stock.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 分析层控制器 — 技术指标 + 缠论 + 量化策略 + 排名筛选
 *
 * 路由前缀: /api/analysis
 */
@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(AnalysisController.class);

    @Autowired
    private AnalysisService analysisService;

    // ==================== 分析结果 CRUD ====================

    @GetMapping("/{assetCode}")
    @Cacheable(cacheNames = "signalReferenceData", key = "'analysis:' + #assetCode + ':' + (#type ?: '')", unless = "#result == null || #result.code != 200")
    public ApiResponse getAnalysis(
            @PathVariable String assetCode,
            @RequestParam(required = false) String type) {
        try {
            com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<AnalysisResult> wrapper =
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
            wrapper.eq(AnalysisResult::getAssetCode, assetCode);
            if (type != null) {
                wrapper.eq(AnalysisResult::getAnalysisType, type);
            }
            wrapper.orderByDesc(AnalysisResult::getAnalysisDate);
            List<AnalysisResult> list = analysisService.list(wrapper);
            return ApiResponse.ok(list);
        } catch (Exception e) {
            log.warn("getAnalysis({}) failed: {}", assetCode, e.getMessage());
            return ApiResponse.ok(java.util.Collections.emptyList());
        }
    }

    @PostMapping("/save")
    public ApiResponse saveAnalysis(@RequestBody AnalysisResult result) {
        boolean saved = analysisService.save(result);
        return saved ? ApiResponse.created(result) : ApiResponse.error("保存失败");
    }

    // ==================== 新增 DELETE 端点 ====================

    @DeleteMapping("/{id}")
    public ApiResponse deleteAnalysis(@PathVariable Long id) {
        boolean removed = analysisService.removeById(id);
        return removed ? ApiResponse.ok("删除成功") : ApiResponse.error("分析记录不存在");
    }

    // ==================== 收益率 ====================

    @GetMapping("/{stockCode}/yearly-return")
    @Cacheable(cacheNames = "infoReport", key = "'yearlyReturn:' + #stockCode + ':' + #years", unless = "#result == null || #result.code != 200")
    public ApiResponse getYearlyReturn(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "3") int years) {
        try { return ApiResponse.ok(analysisService.getYearlyReturn(stockCode, years));
        } catch (Exception e) { log.warn("yearly-return {}: {}", stockCode, e.getMessage()); return ApiResponse.ok(java.util.Collections.emptyList()); }
    }

    @GetMapping("/{stockCode}/monthly-return")
    @Cacheable(cacheNames = "infoReport", key = "'monthlyReturn:' + #stockCode + ':' + #months", unless = "#result == null || #result.code != 200")
    public ApiResponse getMonthlyReturn(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "12") int months) {
        try { return ApiResponse.ok(analysisService.getMonthlyReturn(stockCode, months));
        } catch (Exception e) { log.warn("monthly-return {}: {}", stockCode, e.getMessage()); return ApiResponse.ok(java.util.Collections.emptyList()); }
    }

    @GetMapping("/{stockCode}/trend")
    @Cacheable(cacheNames = "signalReferenceData", key = "'trend:' + #stockCode + ':' + #days", unless = "#result == null || #result.code != 200")
    public ApiResponse getTrend(
            @PathVariable String stockCode,
            @RequestParam(defaultValue = "30") int days) {
        try {
            Map<String, Object> trend = analysisService.getTrendAnalysis(stockCode, days);
            if (trend == null || trend.isEmpty()) return ApiResponse.error("无数据");
            return ApiResponse.ok(trend);
        } catch (Exception e) { log.warn("trend {}: {}", stockCode, e.getMessage()); return ApiResponse.error("无数据"); }
    }

    @PostMapping("/filter")
    public ApiResponse filterStocks(@RequestBody Map<String, Object> conditions) {
        try { return ApiResponse.ok(analysisService.filterStocks(conditions));
        } catch (Exception e) { log.warn("filter: {}", e.getMessage()); return ApiResponse.ok(java.util.Collections.emptyList()); }
    }

    @GetMapping("/correlation")
    public ApiResponse getCorrelation(
            @RequestParam String codeA, @RequestParam String codeB,
            @RequestParam(defaultValue = "60") int days) {
        try { return ApiResponse.ok(Map.of("codeA",codeA,"codeB",codeB,"correlation",analysisService.getCorrelation(codeA,codeB,days)));
        } catch (Exception e) { log.warn("correlation {}/{}: {}", codeA, codeB, e.getMessage()); return ApiResponse.ok(Map.of("correlation", 0.0)); }
    }

    @GetMapping("/sector-ranking")
    public ApiResponse getSectorRanking(@RequestParam(required = false) String tradeDate) {
        try { return ApiResponse.ok(analysisService.getSectorRanking(tradeDate));
        } catch (Exception e) { log.warn("sector-ranking: {}", e.getMessage()); return ApiResponse.ok(java.util.Collections.emptyList()); }
    }

    @GetMapping("/{stockCode}/chanlun")
    @Cacheable(cacheNames = "infoReport", key = "'chanlun:' + #stockCode + ':' + #days + ':' + #type", unless = "#result == null || #result.code != 200")
    public ApiResponse getChanlun(@PathVariable String stockCode, @RequestParam(defaultValue = "365") int days,
                                  @RequestParam(defaultValue = "stock") String type) {
        try {
            // 3-arg 方法已在 AnalysisServiceImpl 中存在，直接传递 preferIndex
            boolean preferIndex = "index".equals(type);
            return ApiResponse.ok(analysisService.getChanlunAnalysis(stockCode, days, preferIndex));
        } catch (Exception e) { log.warn("chanlun {}: {}", stockCode, e.getMessage()); return ApiResponse.ok((Object)null); }
    }
}
