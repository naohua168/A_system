package com.stock.service.impl;

import com.stock.entity.AnalysisResult;
import com.stock.entity.StockDaily;
import com.stock.mapper.AnalysisResultMapper;
import com.stock.mapper.StockDailyMapper;
import com.stock.service.AnalysisService;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class AnalysisServiceImpl implements AnalysisService {

    private final StockDailyMapper stockDailyMapper;
    private final AnalysisResultMapper analysisResultMapper;

    public AnalysisServiceImpl(StockDailyMapper stockDailyMapper,
                               AnalysisResultMapper analysisResultMapper) {
        this.stockDailyMapper = stockDailyMapper;
        this.analysisResultMapper = analysisResultMapper;
    }

    @Override
    public boolean save(AnalysisResult result) {
        return analysisResultMapper.insert(result) > 0;
    }

    @Override
    public List<Map<String, Object>> getYearlyReturn(String stockCode, int years) {
        List<Map<String, Object>> result = new ArrayList<>();
        int currentYear = LocalDate.now().getYear();
        for (int i = 0; i < years; i++) {
            int year = currentYear - i;
            StockDaily first = stockDailyMapper.selectFirstOfYear(stockCode, year);
            StockDaily last = stockDailyMapper.selectLastOfYear(stockCode, year);
            if (first == null || last == null) continue;

            BigDecimal startPrice = first.getClosePrice();
            BigDecimal endPrice = last.getClosePrice();
            if (startPrice == null || endPrice == null || startPrice.compareTo(BigDecimal.ZERO) == 0) continue;

            BigDecimal yearlyReturn = endPrice.subtract(startPrice)
                    .divide(startPrice, 4, RoundingMode.HALF_UP)
                    .multiply(BigDecimal.valueOf(100));

            Map<String, Object> item = new HashMap<>();
            item.put("year", year);
            item.put("yearlyReturn", yearlyReturn.setScale(2, RoundingMode.HALF_UP));
            item.put("startPrice", startPrice);
            item.put("endPrice", endPrice);
            result.add(item);
        }
        return result;
    }

    @Override
    public List<Map<String, Object>> getMonthlyReturn(String stockCode, int months) {
        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusMonths(months);
        List<StockDaily> dailyList = stockDailyMapper.selectByDateRange(stockCode,
                startDate.toString(), endDate.toString());
        dailyList.sort(Comparator.comparing(StockDaily::getTradeDate));

        Map<String, List<StockDaily>> grouped = dailyList.stream()
                .collect(Collectors.groupingBy(d ->
                        d.getTradeDate().format(DateTimeFormatter.ofPattern("yyyy-MM"))));

        List<Map<String, Object>> result = new ArrayList<>();

        for (Map.Entry<String, List<StockDaily>> entry : grouped.entrySet()) {
            List<StockDaily> monthData = entry.getValue();
            monthData.sort(Comparator.comparing(StockDaily::getTradeDate));

            StockDaily first = monthData.get(0);
            StockDaily last = monthData.get(monthData.size() - 1);

            BigDecimal startPrice = first.getClosePrice();
            BigDecimal endPrice = last.getClosePrice();
            if (startPrice == null || endPrice == null || startPrice.compareTo(BigDecimal.ZERO) == 0) continue;

            BigDecimal monthlyReturn = endPrice.subtract(startPrice)
                    .divide(startPrice, 4, RoundingMode.HALF_UP)
                    .multiply(BigDecimal.valueOf(100));

            Map<String, Object> item = new HashMap<>();
            item.put("yearMonth", entry.getKey());
            item.put("monthlyReturn", monthlyReturn.setScale(2, RoundingMode.HALF_UP));
            item.put("avgPrice", monthData.stream()
                    .map(StockDaily::getClosePrice)
                    .filter(Objects::nonNull)
                    .reduce(BigDecimal.ZERO, BigDecimal::add)
                    .divide(BigDecimal.valueOf(monthData.size()), 2, RoundingMode.HALF_UP));
            result.add(item);
        }
        return result;
    }

    // ============================================================
    // 趋势分析
    // ============================================================

    @Override
    public Map<String, Object> getTrendAnalysis(String stockCode, int days) {
        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(days * 2);
        List<StockDaily> dailyList = stockDailyMapper.selectByDateRange(stockCode,
                startDate.toString(), endDate.toString());
        dailyList.sort(Comparator.comparing(StockDaily::getTradeDate));

        if (dailyList.isEmpty()) {
            return Collections.emptyMap();
        }

        List<StockDaily> recentData = dailyList.size() > days
                ? dailyList.subList(dailyList.size() - days, dailyList.size())
                : dailyList;

        List<BigDecimal> ma5 = calculateMA(dailyList, 5);
        List<BigDecimal> ma10 = calculateMA(dailyList, 10);
        List<BigDecimal> ma20 = calculateMA(dailyList, 20);

        String trend = determineTrend(recentData.stream()
                .map(StockDaily::getClosePrice)
                .filter(Objects::nonNull)
                .collect(Collectors.toList()));

        Map<String, Object> result = new HashMap<>();
        result.put("stockCode", stockCode);
        result.put("trend", trend);
        result.put("ma5", ma5.isEmpty() ? BigDecimal.ZERO : ma5.get(ma5.size() - 1));
        result.put("ma10", ma10.isEmpty() ? BigDecimal.ZERO : ma10.get(ma10.size() - 1));
        result.put("ma20", ma20.isEmpty() ? BigDecimal.ZERO : ma20.get(ma20.size() - 1));
        result.put("dataCount", recentData.size());

        return result;
    }

    // ============================================================
    // 股票筛选
    // ============================================================

    @Override
    public List<Map<String, Object>> filterStocks(Map<String, Object> conditions) {
        String industry = (String) conditions.get("industry");
        BigDecimal minPrice = getBigDecimal(conditions, "minPrice");
        BigDecimal maxPrice = getBigDecimal(conditions, "maxPrice");
        BigDecimal minChange = getBigDecimal(conditions, "minChange");
        Integer limit = getInteger(conditions, "limit", 50);

        List<Map<String, Object>> result = stockDailyMapper.selectStocksByFilter(
                industry, minPrice, maxPrice, minChange, limit
        );

        return result == null ? Collections.emptyList() : result;
    }

    // ============================================================
    // 相关性分析
    // ============================================================

    @Override
    public BigDecimal getCorrelation(String code1, String code2, int days) {
        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(days);
        List<StockDaily> list1 = stockDailyMapper.selectByDateRange(code1,
                startDate.toString(), endDate.toString());
        List<StockDaily> list2 = stockDailyMapper.selectByDateRange(code2,
                startDate.toString(), endDate.toString());

        Map<String, BigDecimal> map1 = list1.stream()
                .filter(d -> d.getClosePrice() != null)
                .collect(Collectors.toMap(
                        d -> d.getTradeDate().toString(),
                        StockDaily::getClosePrice));
        Map<String, BigDecimal> map2 = list2.stream()
                .filter(d -> d.getClosePrice() != null)
                .collect(Collectors.toMap(
                        d -> d.getTradeDate().toString(),
                        StockDaily::getClosePrice));

        List<String> commonDates = map1.keySet().stream()
                .filter(map2::containsKey)
                .sorted()
                .collect(Collectors.toList());

        if (commonDates.size() < 5) return BigDecimal.ZERO;

        List<BigDecimal> x = commonDates.stream().map(map1::get).collect(Collectors.toList());
        List<BigDecimal> y = commonDates.stream().map(map2::get).collect(Collectors.toList());

        return calculatePearsonCorrelation(x, y);
    }

    // ============================================================
    // 行业排行
    // ============================================================

    @Override
    public List<Map<String, Object>> getSectorRanking(String tradeDate) {
        List<Map<String, Object>> result = stockDailyMapper.selectSectorRanking(tradeDate);
        if (result == null || result.isEmpty()) {
            String maxDate = stockDailyMapper.selectMaxTradeDate();
            if (maxDate != null) {
                result = stockDailyMapper.selectSectorRanking(maxDate);
            }
        }
        return result == null ? Collections.emptyList() : result;
    }

    // ============================================================
    // 私有工具方法
    // ============================================================

    private List<BigDecimal> calculateMA(List<StockDaily> data, int period) {
        List<BigDecimal> result = new ArrayList<>();
        if (data.size() < period) return result;
        for (int i = period - 1; i < data.size(); i++) {
            BigDecimal sum = BigDecimal.ZERO;
            int validCount = 0;
            for (int j = i - period + 1; j <= i; j++) {
                BigDecimal price = data.get(j).getClosePrice();
                if (price != null) {
                    sum = sum.add(price);
                    validCount++;
                }
            }
            if (validCount > 0) {
                result.add(sum.divide(BigDecimal.valueOf(validCount), 2, RoundingMode.HALF_UP));
            }
        }
        return result;
    }

    private String determineTrend(List<BigDecimal> prices) {
        if (prices.size() < 5) return "unknown";

        // 过滤 null
        List<BigDecimal> clean = prices.stream()
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
        if (clean.size() < 5) return "unknown";

        int half = clean.size() / 2;
        BigDecimal firstHalfAvg = clean.subList(0, half).stream()
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(half), 2, RoundingMode.HALF_UP);
        BigDecimal secondHalfAvg = clean.subList(half, clean.size()).stream()
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(clean.size() - half), 2, RoundingMode.HALF_UP);

        // 防止除零
        if (firstHalfAvg.compareTo(BigDecimal.ZERO) == 0) return "unknown";

        BigDecimal diff = secondHalfAvg.subtract(firstHalfAvg)
                .divide(firstHalfAvg, 4, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100));

        if (diff.compareTo(BigDecimal.valueOf(3)) > 0) return "上升趋势";
        if (diff.compareTo(BigDecimal.valueOf(-3)) < 0) return "下跌趋势";
        return "震荡趋势";
    }

    private BigDecimal calculatePearsonCorrelation(List<BigDecimal> x, List<BigDecimal> y) {
        int n = x.size();
        if (n < 5) return BigDecimal.ZERO;

        BigDecimal sumX = x.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal sumY = y.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal sumXY = BigDecimal.ZERO;
        BigDecimal sumX2 = BigDecimal.ZERO;
        BigDecimal sumY2 = BigDecimal.ZERO;

        for (int i = 0; i < n; i++) {
            BigDecimal xi = x.get(i);
            BigDecimal yi = y.get(i);
            sumXY = sumXY.add(xi.multiply(yi));
            sumX2 = sumX2.add(xi.multiply(xi));
            sumY2 = sumY2.add(yi.multiply(yi));
        }

        // 协方差 = n*sumXY - sumX*sumY
        BigDecimal covariance = sumXY.multiply(BigDecimal.valueOf(n))
                .subtract(sumX.multiply(sumY));

        // 标准差分母
        BigDecimal denomX = sumX2.multiply(BigDecimal.valueOf(n))
                .subtract(sumX.multiply(sumX));
        BigDecimal denomY = sumY2.multiply(BigDecimal.valueOf(n))
                .subtract(sumY.multiply(sumY));

        // 防止浮点精度导致负值
        if (denomX.compareTo(BigDecimal.ZERO) <= 0 || denomY.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }

        double denominator = Math.sqrt(denomX.multiply(denomY).doubleValue());
        if (denominator == 0) return BigDecimal.ZERO;

        double correlation = covariance.doubleValue() / denominator;
        // 截断到 [-1, 1] 范围
        correlation = Math.max(-1.0, Math.min(1.0, correlation));

        return BigDecimal.valueOf(correlation).setScale(4, RoundingMode.HALF_UP);
    }

    /** 从 Map 安全提取 BigDecimal，防止空值 NPE */
    private BigDecimal getBigDecimal(Map<String, Object> map, String key) {
        Object val = map.get(key);
        if (val == null) return null;
        try {
            return new BigDecimal(val.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /** 从 Map 安全提取 Integer */
    private Integer getInteger(Map<String, Object> map, String key, Integer defaultValue) {
        Object val = map.get(key);
        if (val == null) return defaultValue;
        try {
            return Integer.parseInt(val.toString());
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}
