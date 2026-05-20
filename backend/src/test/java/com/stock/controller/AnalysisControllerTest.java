package com.stock.controller;

import com.stock.config.MockWebMvcTest;
import com.stock.service.AnalysisService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.*;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * AnalysisController Web MVC 测试
 * 仅测试 Controller 层的请求映射、参数绑定、异常处理
 */
@MockWebMvcTest(AnalysisController.class)
@AutoConfigureMockMvc(addFilters = false)
class AnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AnalysisService analysisService;

    private List<Map<String, Object>> mockYearlyReturn;

    @BeforeEach
    void setUp() {
        mockYearlyReturn = new ArrayList<>();
        Map<String, Object> item = new HashMap<>();
        item.put("year", 2025);
        item.put("yearlyReturn", new BigDecimal("5.00"));
        item.put("startPrice", new BigDecimal("10.00"));
        item.put("endPrice", new BigDecimal("10.50"));
        mockYearlyReturn.add(item);
    }

    @Test
    @DisplayName("GET /api/analysis/{stockCode}/yearly-return - 正常返回")
    void testGetYearlyReturn() throws Exception {
        when(analysisService.getYearlyReturn("000001", 3)).thenReturn(mockYearlyReturn);

        mockMvc.perform(get("/api/analysis/000001/yearly-return")
                        .param("years", "3")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].year").value(2025))
                .andExpect(jsonPath("$.data[0].yearlyReturn").value(5.00));
    }

    @Test
    @DisplayName("GET /api/analysis/{stockCode}/yearly-return - 默认参数")
    void testGetYearlyReturn_DefaultParams() throws Exception {
        when(analysisService.getYearlyReturn("000001", 3)).thenReturn(mockYearlyReturn);

        mockMvc.perform(get("/api/analysis/000001/yearly-return")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/analysis/{stockCode}/monthly-return - 正常返回")
    void testGetMonthlyReturn() throws Exception {
        when(analysisService.getMonthlyReturn("000001", 12)).thenReturn(mockYearlyReturn);

        mockMvc.perform(get("/api/analysis/000001/monthly-return")
                        .param("months", "12")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].year").value(2025));
    }

    @Test
    @DisplayName("GET /api/analysis/{stockCode}/monthly-return - 默认参数")
    void testGetMonthlyReturn_DefaultParams() throws Exception {
        when(analysisService.getMonthlyReturn("000001", 12)).thenReturn(mockYearlyReturn);

        mockMvc.perform(get("/api/analysis/000001/monthly-return")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/analysis/{stockCode}/trend - 趋势分析")
    void testGetTrend() throws Exception {
        Map<String, Object> trend = new HashMap<>();
        trend.put("stockCode", "000001");
        trend.put("trend", "上升趋势");
        trend.put("currentPrice", new BigDecimal("10.50"));

        when(analysisService.getTrendAnalysis("000001", 30)).thenReturn(trend);

        mockMvc.perform(get("/api/analysis/000001/trend")
                        .param("days", "30")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.trend").value("上升趋势"));
    }

    @Test
    @DisplayName("POST /api/analysis/filter - 股票筛选")
    void testFilterStocks() throws Exception {
        List<Map<String, Object>> filterResult = new ArrayList<>();
        Map<String, Object> item = new HashMap<>();
        item.put("stockCode", "000001");
        filterResult.add(item);

        when(analysisService.filterStocks(anyMap())).thenReturn(filterResult);

        mockMvc.perform(post("/api/analysis/filter")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"industry\":\"金融\",\"minPrice\":10}")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].stockCode").value("000001"));
    }

    @Test
    @DisplayName("GET /api/analysis/correlation - 相关性分析")
    void testGetCorrelation() throws Exception {
        when(analysisService.getCorrelation("000001", "600519", 60))
                .thenReturn(new BigDecimal("0.8500"));

        mockMvc.perform(get("/api/analysis/correlation")
                        .param("codeA", "000001")
                        .param("codeB", "600519")
                        .param("days", "60")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.correlation").value(0.85));
    }

    @Test
    @DisplayName("GET /api/analysis/sector-ranking - 行业排行")
    void testGetSectorRanking() throws Exception {
        List<Map<String, Object>> ranking = new ArrayList<>();
        Map<String, Object> sector = new HashMap<>();
        sector.put("industry", "金融");
        sector.put("avgChangePct", 2.5);
        ranking.add(sector);

        when(analysisService.getSectorRanking("2025-01-10")).thenReturn(ranking);

        mockMvc.perform(get("/api/analysis/sector-ranking")
                        .param("tradeDate", "2025-01-10")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].industry").value("金融"));
    }

    @Test
    @DisplayName("GET /api/analysis/{assetCode} - 获取分析结果")
    void testGetAnalysis() throws Exception {
        mockMvc.perform(get("/api/analysis/000001")
                        .param("type", "trend")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("POST /api/analysis/save - 保存分析结果")
    void testSaveAnalysis() throws Exception {
        when(analysisService.save(any())).thenReturn(true);

        mockMvc.perform(post("/api/analysis/save")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"assetCode\":\"000001\",\"analysisType\":\"trend\"}")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(201))
                .andExpect(jsonPath("$.message").value("created"));
    }

    // ==================== 新增 DELETE 端点测试 ====================

    @Test
    @DisplayName("DELETE /api/analysis/{id} - 删除分析结果 - 成功")
    void testDeleteAnalysis_Success() throws Exception {
        when(analysisService.removeById(1L)).thenReturn(true);

        mockMvc.perform(delete("/api/analysis/1")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"));
    }

    @Test
    @DisplayName("DELETE /api/analysis/{id} - 删除分析结果 - 不存在")
    void testDeleteAnalysis_NotFound() throws Exception {
        when(analysisService.removeById(999L)).thenReturn(false);

        mockMvc.perform(delete("/api/analysis/999")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("分析记录不存在"));
    }
}
