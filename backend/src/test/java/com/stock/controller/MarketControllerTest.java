package com.stock.controller;

import com.stock.config.MockWebMvcTest;
import com.stock.mapper.StockDailyMapper;
import com.stock.service.StockService;
import com.stock.service.StockDailyService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * MarketController — 行情 API 测试
 */
@MockWebMvcTest(MarketController.class)
@AutoConfigureMockMvc(addFilters = false)
class MarketControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private StockService stockService;

    @MockBean
    private StockDailyService stockDailyService;

    @MockBean
    private StockDailyMapper stockDailyMapper;

    @MockBean
    private JdbcTemplate jdbcTemplate;

    // ============================================================
    // 1. 股票列表
    // ============================================================

    @Test
    @DisplayName("GET /api/market/list - 默认分页参数")
    void testListDefaultParams() throws Exception {
        mockMvc.perform(get("/api/market/list")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/market/list - 自定义分页参数")
    void testListCustomParams() throws Exception {
        mockMvc.perform(get("/api/market/list")
                        .param("page", "2")
                        .param("size", "50")
                        .param("keyword", "平安")
                        .param("industry", "银行")
                        .param("sortField", "changePct")
                        .param("sortOrder", "desc")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/market/list - 无效页码返回默认列表")
    void testListInvalidPage() throws Exception {
        mockMvc.perform(get("/api/market/list")
                        .param("page", "-1")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 2. 个股详情
    // ============================================================

    @Test
    @DisplayName("GET /api/market/{code} - 正常返回")
    void testDetailFound() throws Exception {
        mockMvc.perform(get("/api/market/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/market/{code} - 空代码返回默认处理")
    void testDetailEmptyCode() throws Exception {
        mockMvc.perform(get("/api/market/ ")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 3. K 线数据
    // ============================================================

    @Test
    @DisplayName("GET /api/market/kline/{code} - 默认天数")
    void testKlineDefault() throws Exception {
        mockMvc.perform(get("/api/market/kline/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/market/kline/{code} - 自定义天数")
    void testKlineCustomDays() throws Exception {
        mockMvc.perform(get("/api/market/kline/000001")
                        .param("days", "120")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 4. 搜索
    // ============================================================

    @Test
    @DisplayName("GET /api/market/search - 关键字搜索")
    void testSearch() throws Exception {
        mockMvc.perform(get("/api/market/search")
                        .param("keyword", "平安")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/market/search - 空关键字")
    void testSearchEmptyKeyword() throws Exception {
        mockMvc.perform(get("/api/market/search")
                        .param("keyword", "")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 5. 行业列表
    // ============================================================

    @Test
    @DisplayName("GET /api/market/industries - 正常返回")
    void testIndustries() throws Exception {
        mockMvc.perform(get("/api/market/industries")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 6. 行业涨跌排行
    // ============================================================

    @Test
    @DisplayName("GET /api/market/sector-ranking - 正常返回")
    void testSectorRanking() throws Exception {
        mockMvc.perform(get("/api/market/sector-ranking")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 7. 板块 K 线聚合
    // ============================================================

    @Test
    @DisplayName("GET /api/market/sector-kline - 正常返回")
    void testSectorKline() throws Exception {
        mockMvc.perform(get("/api/market/sector-kline")
                        .param("industry", "银行")
                        .param("days", "60")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/market/sector-kline - 缺少行业参数返回默认")
    void testSectorKlineMissingIndustry() throws Exception {
        mockMvc.perform(get("/api/market/sector-kline")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    // ============================================================
    // 8. 最近交易日
    // ============================================================

    @Test
    @DisplayName("GET /api/market/max-date - 正常返回")
    void testMaxDate() throws Exception {
        mockMvc.perform(get("/api/market/max-date")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }
}
