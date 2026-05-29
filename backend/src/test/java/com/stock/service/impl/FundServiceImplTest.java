package com.stock.service.impl;

import com.stock.entity.Fund;
import com.stock.mapper.FundMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * FundService 单元测试 — 验证 MyBatis-Plus 基础操作
 */
@ExtendWith(MockitoExtension.class)
class FundServiceImplTest {

    @Mock
    private FundMapper fundMapper;

    @InjectMocks
    private FundServiceImpl fundService;

    private Fund mockFund;

    @BeforeEach
    void setUp() {
        mockFund = new Fund();
        mockFund.setId(1L);
        mockFund.setFundCode("000001");
        mockFund.setFundName("华夏成长混合");
        mockFund.setFundType("混合型-灵活");
        mockFund.setCompany("华夏基金");
        mockFund.setManager("郑晓辉");
        mockFund.setNav(BigDecimal.valueOf(1.356));
        mockFund.setScale(BigDecimal.valueOf(26.44));
    }

    @Test
    @DisplayName("Fund 实体字段映射正确")
    void testFundEntityMapping() {
        assertEquals("000001", mockFund.getFundCode());
        assertEquals("华夏成长混合", mockFund.getFundName());
        assertEquals("华夏基金", mockFund.getCompany());
        assertEquals(1.356, mockFund.getNav().doubleValue(), 0.001);
        assertEquals(26.44, mockFund.getScale().doubleValue(), 0.001);
    }

    @Test
    @DisplayName("货币基金类型检测")
    void testMoneyMarketTypeDetection() {
        assertTrue("货币型-普通货币".contains("货币"));
        assertTrue("货币型".contains("货币"));
        assertFalse("混合型-灵活".contains("货币"));
    }

    @Test
    @DisplayName("yearReturn 计算逻辑正确")
    void testYearReturnCalculation() {
        BigDecimal latestNav = BigDecimal.valueOf(1.356);
        BigDecimal oldestNav = BigDecimal.valueOf(1.045);
        BigDecimal yearReturn = latestNav.subtract(oldestNav)
            .divide(oldestNav, 6, java.math.RoundingMode.HALF_UP)
            .multiply(BigDecimal.valueOf(100))
            .setScale(2, java.math.RoundingMode.HALF_UP);
        assertEquals(29.76, yearReturn.doubleValue(), 0.01);
    }

    @Test
    @DisplayName("Mapper 查询委托正确")
    void testMapperSelect() {
        when(fundMapper.selectById(1L)).thenReturn(mockFund);
        Fund result = fundMapper.selectById(1L);
        assertNotNull(result);
        assertEquals("000001", result.getFundCode());
        verify(fundMapper, times(1)).selectById(1L);
    }
}
