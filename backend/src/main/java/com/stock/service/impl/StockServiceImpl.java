package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.Stock;
import com.stock.mapper.StockMapper;
import com.stock.service.StockService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Service
@CacheConfig(cacheNames = "stock")
public class StockServiceImpl extends ServiceImpl<StockMapper, Stock> implements StockService {

    @Cacheable(key = "'filter:' + #keyword + ':' + #industry + ':' + #market + ':' + #minPrice + ':' + #maxPrice + ':' + #sortField + ':' + #sortOrder + ':' + #limit + ':' + #offset",
               unless = "#result == null || #result.isEmpty()")
    public List<Map<String, Object>> selectByFilter(String keyword, String industry, String market,
                                                     BigDecimal minPrice, BigDecimal maxPrice,
                                                     BigDecimal minPe, BigDecimal maxPe,
                                                     String sortField, String sortOrder,
                                                     Integer limit, Integer offset) {
        return baseMapper.selectByFilter(keyword, industry, market, minPrice, maxPrice, minPe, maxPe,
                sortField, sortOrder, limit, offset);
    }

    @Cacheable(key = "'industryStats'", unless = "#result == null || #result.isEmpty()")
    public List<Map<String, Object>> selectIndustryStats() {
        return baseMapper.selectIndustryStats();
    }

    @Cacheable(key = "'marketCap:' + #minCap + ':' + #maxCap + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<Map<String, Object>> selectByMarketCap(BigDecimal minCap, BigDecimal maxCap, Integer limit) {
        return baseMapper.selectByMarketCap(minCap, maxCap, limit);
    }

    @CacheEvict(allEntries = true)
    public void clearCache() {
        // 清空该缓存区域的所有缓存
    }
}
