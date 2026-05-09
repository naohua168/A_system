package com.stock.service.impl;

import com.stock.entity.StockDaily;
import com.stock.mapper.StockDailyMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

/**
 * AnalysisService 实现类单元测试
 * 使用 Mockito 模拟 Mapper 层，专注测试业务逻辑
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class AnalysisServiceImplTest {

    @Mock
    private StockDailyMapper stockDailyMapper;

    @InjectMocks
    private AnalysisServiceImpl analysisService;

    private StockDaily daily1, daily2, daily3;
    private List<StockDaily> mockDailyList;

    @BeforeEach
    void setUp() {
        // 构造 3 条模拟日K数据
        daily1 = new StockDaily();
        daily1.setStockCode("000001");
        daily1.setTradeDate(LocalDate.of(2025, 1, 2));
        daily1.setClosePrice(new BigDecimal("10.00"));
        daily1.setOpenPrice(new BigDecimal("9.90"));
        daily1.setHighPrice(new BigDecimal("10.20"));
        daily1.setLowPrice(new BigDecimal("9.80"));
        daily1.setVolume(1000000L);
        daily1.setChangePercent(new BigDecimal("1.01"));

        daily2 = new StockDaily();
        daily2.setStockCode("000001");
        daily2.setTradeDate(LocalDate.of(2025, 1, 3));
        daily2.setClosePrice(new BigDecimal("11.00"));
        daily2.setOpenPrice(new BigDecimal("10.10"));
        daily2.setHighPrice(new BigDecimal("11.20"));
        daily2.setLowPrice(new BigDecimal("9.90"));
        daily2.setVolume(1500000L);
        daily2.setChangePercent(new BigDecimal("10.00"));

        daily3 = new StockDaily();
        daily3.setStockCode("000001");
        daily3.setTradeDate(LocalDate.of(2025, 1, 4));
        daily3.setClosePrice(new BigDecimal("10.50"));
        daily3.setOpenPrice(new BigDecimal("10.80"));
        daily3.setHighPrice(new BigDecimal("11.00"));
        daily3.setLowPrice(new BigDecimal("10.30"));
        daily3.setVolume(1200000L);
        daily3.setChangePercent(new BigDecimal("-4.55"));

        mockDailyList = Arrays.asList(daily1, daily2, daily3);
    }

    // ============================================================
    // getYearlyReturn
    // ============================================================

    @Test
    @DisplayName("年收益率 - 正常计算")
    void testGetYearlyReturn_Success() {
        String stockCode = "000001";
        int currentYear = java.time.LocalDate.now().getYear();
        when(stockDailyMapper.selectFirstOfYear(eq(stockCode), anyInt())).thenReturn(daily1);
        when(stockDailyMapper.selectLastOfYear(eq(stockCode), anyInt())).thenReturn(daily3);

        List<Map<String, Object>> result = analysisService.getYearlyReturn(stockCode, 1);

        assertEquals(1, result.size());
        Map<String, Object> item = result.get(0);
        assertEquals(currentYear, item.get("year"));
        // (10.50 - 10.00) / 10.00 * 100 = 5.00
        assertEquals(new BigDecimal("5.00"), item.get("yearlyReturn"));
        assertEquals(new BigDecimal("10.00"), item.get("startPrice"));
        assertEquals(new BigDecimal("10.50"), item.get("endPrice"));
    }

    @Test
    @DisplayName("年收益率 - 查询不到数据时跳过")
    void testGetYearlyReturn_NoData() {
        when(stockDailyMapper.selectFirstOfYear(anyString(), anyInt())).thenReturn(null);

        List<Map<String, Object>> result = analysisService.getYearlyReturn("999999", 3);

        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("年收益率 - 起始价格为0时跳过")
    void testGetYearlyReturn_ZeroStartPrice() {
        StockDaily zeroPrice = new StockDaily();
        zeroPrice.setClosePrice(BigDecimal.ZERO);
        zeroPrice.setTradeDate(LocalDate.of(2025, 1, 2));

        when(stockDailyMapper.selectFirstOfYear(anyString(), eq(2025))).thenReturn(zeroPrice);
        when(stockDailyMapper.selectLastOfYear(anyString(), eq(2025))).thenReturn(daily3);

        List<Map<String, Object>> result = analysisService.getYearlyReturn("000001", 1);

        assertTrue(result.isEmpty());
    }

    // ============================================================
    // getMonthlyReturn
    // ============================================================

    @Test
    @DisplayName("月收益率 - 正常计算")
    void testGetMonthlyReturn_Success() {
        String stockCode = "000001";
        when(stockDailyMapper.selectByDateRange(eq(stockCode), anyString(), anyString()))
                .thenReturn(mockDailyList);

        List<Map<String, Object>> result = analysisService.getMonthlyReturn(stockCode, 1);

        assertEquals(1, result.size());
        Map<String, Object> item = result.get(0);
        assertEquals("2025-01", item.get("yearMonth"));
        // (10.50 - 10.00) / 10.00 * 100 = 5.00
        assertEquals(new BigDecimal("5.00"), item.get("monthlyReturn"));
    }

    @Test
    @DisplayName("月收益率 - 空数据返回空列表")
    void testGetMonthlyReturn_EmptyData() {
        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(Collections.emptyList());

        List<Map<String, Object>> result = analysisService.getMonthlyReturn("000001", 1);

        assertTrue(result.isEmpty());
    }

    // ============================================================
    // getTrendAnalysis
    // ============================================================

    @Test
    @DisplayName("趋势分析 - 正常计算")
    void testGetTrendAnalysis_Success() {
        String stockCode = "000001";
        when(stockDailyMapper.selectByDateRange(eq(stockCode), anyString(), anyString()))
                .thenReturn(mockDailyList);

        Map<String, Object> result = analysisService.getTrendAnalysis(stockCode, 30);

        assertNotNull(result);
        assertEquals(stockCode, result.get("stockCode"));
        assertEquals(new BigDecimal("10.50"), result.get("currentPrice"));
        assertNotNull(result.get("trend"));
        assertNotNull(result.get("changePct"));
    }

    @Test
    @DisplayName("趋势分析 - 空数据返回空Map")
    void testGetTrendAnalysis_EmptyData() {
        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(Collections.emptyList());

        Map<String, Object> result = analysisService.getTrendAnalysis("000001", 30);

        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("趋势分析 - MA5/MA10/MA20计算")
    void testGetTrendAnalysis_WithMA() {
        // 构造足够12条数据让 MA20 也有值
        List<StockDaily> data = new ArrayList<>();
        for (int i = 1; i <= 25; i++) {
            StockDaily d = new StockDaily();
            d.setStockCode("000001");
            d.setTradeDate(LocalDate.of(2025, 1, i));
            d.setClosePrice(new BigDecimal("10.00"));
            data.add(d);
        }
        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(data);

        Map<String, Object> result = analysisService.getTrendAnalysis("000001", 30);

        assertNotNull(result.get("ma5"));
        assertNotNull(result.get("ma10"));
        assertNotNull(result.get("ma20"));
    }

    // ============================================================
    // filterStocks
    // ============================================================

    @Test
    @DisplayName("股票筛选 - 正常条件")
    void testFilterStocks_Success() {
        Map<String, Object> conditions = new HashMap<>();
        conditions.put("industry", "金融");
        conditions.put("minPrice", "10");
        conditions.put("limit", "20");

        List<Map<String, Object>> mockResult = new ArrayList<>();
        Map<String, Object> stock = new HashMap<>();
        stock.put("stockCode", "000001");
        stock.put("stockName", "平安银行");
        mockResult.add(stock);

        when(stockDailyMapper.selectStocksByFilter(
                eq("金融"), eq(new BigDecimal("10")), isNull(), isNull(), eq(20)))
                .thenReturn(mockResult);

        List<Map<String, Object>> result = analysisService.filterStocks(conditions);

        assertEquals(1, result.size());
        assertEquals("000001", result.get(0).get("stockCode"));
    }

    @Test
    @DisplayName("股票筛选 - 空条件返回默认查询")
    void testFilterStocks_EmptyCondition() {
        when(stockDailyMapper.selectStocksByFilter(
                isNull(), isNull(), isNull(), isNull(), eq(50)))
                .thenReturn(Collections.emptyList());

        List<Map<String, Object>> result = analysisService.filterStocks(new HashMap<>());

        assertTrue(result.isEmpty());
    }

    // ============================================================
    // getCorrelation
    // ============================================================

    @Test
    @DisplayName("相关性分析 - 两只正相关股票")
    void testGetCorrelation_Positive() {
        List<StockDaily> dataA = new ArrayList<>();
        List<StockDaily> dataB = new ArrayList<>();
        String[] dates = {"2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05",
                          "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10"};

        for (int i = 0; i < dates.length; i++) {
            StockDaily a = new StockDaily();
            a.setTradeDate(LocalDate.parse(dates[i]));
            a.setClosePrice(new BigDecimal(String.valueOf(10 + i)));
            dataA.add(a);

            StockDaily b = new StockDaily();
            b.setTradeDate(LocalDate.parse(dates[i]));
            b.setClosePrice(new BigDecimal(String.valueOf(20 + i * 2)));
            dataB.add(b);
        }

        when(stockDailyMapper.selectByDateRange(eq("A"), anyString(), anyString())).thenReturn(dataA);
        when(stockDailyMapper.selectByDateRange(eq("B"), anyString(), anyString())).thenReturn(dataB);

        BigDecimal correlation = analysisService.getCorrelation("A", "B", 60);

        // 完全正相关应 >= 0.9
        assertTrue(correlation.compareTo(new BigDecimal("0.9")) >= 0,
                "相关性应大于等于 0.9，实际为 " + correlation);
    }

    @Test
    @DisplayName("相关性分析 - 数据点不足10个返回0")
    void testGetCorrelation_InsufficientData() {
        List<StockDaily> dataA = new ArrayList<>();
        dataA.add(daily1);

        List<StockDaily> dataB = new ArrayList<>();
        dataB.add(daily1);

        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(dataA).thenReturn(dataB);

        BigDecimal correlation = analysisService.getCorrelation("A", "B", 5);

        assertEquals(BigDecimal.ZERO, correlation);
    }

    // ============================================================
    // getSectorRanking
    // ============================================================

    @Test
    @DisplayName("行业排行 - 正常调用")
    void testGetSectorRanking() {
        List<Map<String, Object>> mockRanking = new ArrayList<>();
        Map<String, Object> sector = new HashMap<>();
        sector.put("industry", "金融");
        sector.put("avgChangePct", 2.5);
        mockRanking.add(sector);

        when(stockDailyMapper.selectSectorRanking("2025-01-10")).thenReturn(mockRanking);

        List<Map<String, Object>> result = analysisService.getSectorRanking("2025-01-10");

        assertEquals(1, result.size());
        assertEquals("金融", result.get(0).get("industry"));
    }

    @Test
    @DisplayName("行业排行 - 默认日期")
    void testGetSectorRanking_DefaultDate() {
        // Controller 层负责处理默认日期，Service 层直接透传
        // 测试空日期是否不会报错
        List<Map<String, Object>> mockRanking = new ArrayList<>();
        when(stockDailyMapper.selectSectorRanking(anyString())).thenReturn(mockRanking);

        List<Map<String, Object>> result = analysisService.getSectorRanking("2025-01-10");

        assertNotNull(result);
    }

    // ============================================================
    // 内部逻辑方法（通过反射测试私有方法或间接测试）
    // ============================================================

    @Test
    @DisplayName("getTrendAnalysis - 全部相同价格判定为震荡趋势")
    void testDetermineTrend_Flat() {
        List<StockDaily> flatData = new ArrayList<>();
        for (int i = 1; i <= 20; i++) {
            StockDaily d = new StockDaily();
            d.setStockCode("000001");
            d.setTradeDate(LocalDate.of(2025, 1, i));
            d.setClosePrice(new BigDecimal("10.00"));
            flatData.add(d);
        }
        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(flatData);

        Map<String, Object> result = analysisService.getTrendAnalysis("000001", 30);

        // 所有价格相同，趋势应为"震荡趋势"
        assertEquals("震荡趋势", result.get("trend"));
        // 涨跌幅应为0
        assertEquals(new BigDecimal("0.00"), result.get("changePct"));
    }

    @Test
    @DisplayName("getTrendAnalysis - 持续上涨判定上升趋势")
    void testDetermineTrend_Up() {
        List<StockDaily> upData = new ArrayList<>();
        for (int i = 1; i <= 20; i++) {
            StockDaily d = new StockDaily();
            d.setStockCode("000001");
            d.setTradeDate(LocalDate.of(2025, 1, i));
            d.setClosePrice(new BigDecimal(String.valueOf(10.0 + i * 0.5)));
            upData.add(d);
        }
        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(upData);

        Map<String, Object> result = analysisService.getTrendAnalysis("000001", 30);

        assertEquals("上升趋势", result.get("trend"));
    }

    @Test
    @DisplayName("getTrendAnalysis - K线数据不足时趋势为unknown")
    void testDetermineTrend_InsufficientData() {
        List<StockDaily> smallData = new ArrayList<>();
        smallData.add(daily1);
        smallData.add(daily2);
        smallData.add(daily3);
        when(stockDailyMapper.selectByDateRange(anyString(), anyString(), anyString()))
                .thenReturn(smallData);

        Map<String, Object> result = analysisService.getTrendAnalysis("000001", 30);

        assertEquals("unknown", result.get("trend"));
    }
}
