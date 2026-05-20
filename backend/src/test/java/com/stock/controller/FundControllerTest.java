package com.stock.controller;

import com.stock.config.MockWebMvcTest;
import com.stock.entity.Fund;
import com.stock.entity.FundNav;
import com.stock.entity.FundHolding;
import com.stock.service.FundService;
import com.stock.service.FundNavService;
import com.stock.service.FundHoldingService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Collections;
import java.util.List;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * FundController — 基金 API 测试
 */
@MockWebMvcTest(FundController.class)
@AutoConfigureMockMvc(addFilters = false)
class FundControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private FundService fundService;

    @MockBean
    private FundNavService fundNavService;

    @MockBean
    private FundHoldingService fundHoldingService;

    @Test
    @DisplayName("GET /api/fund/list - 默认参数")
    void testListDefault() throws Exception {
        mockMvc.perform(get("/api/fund/list")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/fund/list - 按类型筛选")
    void testListByType() throws Exception {
        mockMvc.perform(get("/api/fund/list")
                        .param("fundType", "股票型")
                        .param("page", "1")
                        .param("size", "20")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/fund/{code} - 正常返回")
    void testDetailFound() throws Exception {
        Fund mockFund = new Fund();
        mockFund.setFundCode("000001");
        mockFund.setFundName("华夏成长混合");
        when(fundService.getOne(any())).thenReturn(mockFund);

        mockMvc.perform(get("/api/fund/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.fundName").value("华夏成长混合"));
    }

    @Test
    @DisplayName("GET /api/fund/{code} - 基金不存在返回 ApiResponse code=404")
    void testDetailNotFound() throws Exception {
        when(fundService.getOne(any())).thenReturn(null);
        mockMvc.perform(get("/api/fund/999999")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(404));
    }

    @Test
    @DisplayName("GET /api/fund/{code}/nav - 正常返回")
    void testNav() throws Exception {
        FundNav nav = new FundNav();
        nav.setFundCode("000001");
        nav.setNavDate(LocalDate.of(2025, 1, 2));
        nav.setNav(BigDecimal.valueOf(1.5));
        when(fundNavService.getLatest(eq("000001"), anyInt())).thenReturn(Collections.singletonList(nav));

        mockMvc.perform(get("/api/fund/000001/nav")
                        .param("days", "30")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/fund/{code}/nav - 空净值列表")
    void testNavEmpty() throws Exception {
        when(fundNavService.getLatest(anyString(), anyInt())).thenReturn(Collections.emptyList());

        mockMvc.perform(get("/api/fund/000001/nav")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("GET /api/fund/{code}/holdings - 正常返回")
    void testHoldings() throws Exception {
        FundHolding holding = new FundHolding();
        holding.setFundCode("000001");
        holding.setStockCode("600519");
        holding.setStockName("贵州茅台");
        holding.setRatio(BigDecimal.valueOf(8.5));
        when(fundHoldingService.getTopHoldings(eq("000001"), anyInt())).thenReturn(Collections.singletonList(holding));

        mockMvc.perform(get("/api/fund/000001/holdings")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].stockName").value("贵州茅台"))
                .andExpect(jsonPath("$.data[0].ratio").value(8.5));
    }

    @Test
    @DisplayName("GET /api/fund/{code}/holdings - 空持仓")
    void testHoldingsEmpty() throws Exception {
        when(fundHoldingService.getTopHoldings(anyString(), anyInt())).thenReturn(Collections.emptyList());

        mockMvc.perform(get("/api/fund/000001/holdings")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }
}
