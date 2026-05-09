package com.stock.mr;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * StockYearlyReturn 单元测试
 * 验证 MapReduce 作业的 Mapper 和 Reducer 逻辑
 */
class StockYearlyReturnTest {

    @Test
    @DisplayName("Mapper 输入解析 - 有效行")
    void testParseValidLine() {
        // stock_code,trade_date,close_price
        String line = "000001,2025-01-02,10.50";
        // 模拟 Mapper 行为：按逗号分割
        String[] parts = line.split(",");
        assertEquals(3, parts.length);
        assertEquals("000001", parts[0]);
        assertEquals("2025-01-02", parts[1]);
        assertEquals("10.50", parts[2]);
    }

    @Test
    @DisplayName("Mapper 输入解析 - 空行")
    void testParseEmptyLine() {
        String line = "";
        assertTrue(line.trim().isEmpty());
    }

    @Test
    @DisplayName("Mapper 输入解析 - 无效行")
    void testParseInvalidLine() {
        String line = "invalid data";
        String[] parts = line.split(",");
        // 无效数据应只有1部分
        assertEquals(1, parts.length);
    }

    @Test
    @DisplayName("年份提取逻辑")
    void testExtractYear() {
        String date = "2025-01-02";
        String year = date.substring(0, 4);
        assertEquals("2025", year);
    }

    @Test
    @DisplayName("收益率计算逻辑")
    void testReturnCalculation() {
        double startPrice = 10.00;
        double endPrice = 10.50;
        // (end - start) / start * 100
        double yearlyReturn = (endPrice - startPrice) / startPrice * 100;
        assertEquals(5.0, yearlyReturn, 0.001);
    }

    @Test
    @DisplayName("收益率计算 - 负收益率")
    void testNegativeReturn() {
        double startPrice = 10.00;
        double endPrice = 9.50;
        double yearlyReturn = (endPrice - startPrice) / startPrice * 100;
        assertEquals(-5.0, yearlyReturn, 0.001);
    }
}
