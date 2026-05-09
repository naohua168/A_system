package com.stock.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.stock.entity.Stock;
import com.stock.entity.StockDaily;
import com.stock.service.StockDailyService;
import com.stock.service.StockService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.*;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * StockController Web MVC 测试
 */
@WebMvcTest(StockController.class)
class StockControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private StockService stockService;

    @MockBean
    private StockDailyService stockDailyService;

    @Test
    @DisplayName("GET /api/stock/list - 股票列表")
    void testGetStockList() throws Exception {
        mockMvc.perform(get("/api/stock/list")
                        .param("page", "1")
                        .param("size", "20")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/stock/{code} - 股票详情")
    void testGetStockByCode() throws Exception {
        Stock stock = new Stock();
        stock.setStockCode("000001");
        stock.setStockName("平安银行");

        when(stockService.getOne(any(LambdaQueryWrapper.class))).thenReturn(stock);

        mockMvc.perform(get("/api/stock/000001")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("GET /api/stock/kline/{code} - K线数据")
    void testGetKlineData() throws Exception {
        when(stockDailyService.getLatestDays(eq("000001"), eq(60)))
                .thenReturn(Collections.emptyList());

        mockMvc.perform(get("/api/stock/kline/000001")
                        .param("days", "60")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }
}
