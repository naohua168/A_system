package com.stock.controller;

import com.stock.config.MockWebMvcTest;
import com.stock.service.SignalDataService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * SignalDataController — 信号数据 API 测试
 */
@MockWebMvcTest(SignalDataController.class)
@AutoConfigureMockMvc(addFilters = false)
class SignalDataControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private SignalDataService signalDataService;

    // ============================================================
    // 1. 题材归因
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/hot-reason - 正常返回")
    void testHotReason() throws Exception {
        mockMvc.perform(get("/api/signal/hot-reason")
                        .param("date", "2025-01-10")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/hot-reason - 无日期参数（默认）")
    void testHotReasonDefault() throws Exception {
        mockMvc.perform(get("/api/signal/hot-reason")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/hot-reason/dates - 可用日期")
    void testHotReasonDates() throws Exception {
        mockMvc.perform(get("/api/signal/hot-reason/dates")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 2. 龙虎榜
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/dragon-tiger/daily - 正常返回")
    void testDragonTigerDaily() throws Exception {
        mockMvc.perform(get("/api/signal/dragon-tiger/daily")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/dragon-tiger/stock/{code} - 个股龙虎榜")
    void testDragonTigerByStock() throws Exception {
        mockMvc.perform(get("/api/signal/dragon-tiger/stock/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/dragon-tiger/detail - 龙虎榜明细")
    void testDragonTigerDetail() throws Exception {
        mockMvc.perform(get("/api/signal/dragon-tiger/detail")
                        .param("tradeDate", "2025-01-10")
                        .param("stockCode", "000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 3. 北向资金
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/northbound/latest - 最新流向")
    void testNorthboundLatest() throws Exception {
        mockMvc.perform(get("/api/signal/northbound/latest")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/northbound/date - 按日期查询（Mock 无数据返回 404）")
    void testNorthboundByDate() throws Exception {
        mockMvc.perform(get("/api/signal/northbound/date")
                        .param("tradeDate", "2025-01-10")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isNotFound());
    }

    // ============================================================
    // 4. 限售解禁
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/lockup/stock/{code} - 个股解禁")
    void testLockupByStock() throws Exception {
        mockMvc.perform(get("/api/signal/lockup/stock/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/lockup/upcoming - 即将解禁")
    void testLockupUpcoming() throws Exception {
        mockMvc.perform(get("/api/signal/lockup/upcoming")
                        .param("days", "30")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 5. 资金流向
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/fund-flow/{code} - 个股资金流向")
    void testFundFlow() throws Exception {
        mockMvc.perform(get("/api/signal/fund-flow/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 6. 行业对比
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/industry-compare - 正常返回")
    void testIndustryCompare() throws Exception {
        mockMvc.perform(get("/api/signal/industry-compare")
                        .param("date", "2025-01-10")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/signal/industry-compare/dates - 可用日期")
    void testIndustryCompareDates() throws Exception {
        mockMvc.perform(get("/api/signal/industry-compare/dates")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 7. 概念板块
    // ============================================================

    @Test
    @DisplayName("GET /api/signal/concept-blocks/{code} - 概念板块归属")
    void testConceptBlocks() throws Exception {
        mockMvc.perform(get("/api/signal/concept-blocks/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }
}
