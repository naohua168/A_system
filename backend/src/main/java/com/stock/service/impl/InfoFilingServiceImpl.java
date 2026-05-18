package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoFiling;
import com.stock.mapper.InfoFilingMapper;
import com.stock.service.InfoFilingService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoFiling")
public class InfoFilingServiceImpl extends ServiceImpl<InfoFilingMapper, InfoFiling>
        implements InfoFilingService {

    @Override
    @Cacheable(key = "'byStock:' + #code + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<InfoFiling> getByStock(String code, int limit) {
        return baseMapper.selectByStock(code, limit);
    }

    @Override
    @Cacheable(key = "'byRange:' + #code + ':' + #startDate + ':' + #endDate", unless = "#result == null || #result.isEmpty()")
    public List<InfoFiling> getByStockAndDateRange(String code, String startDate, String endDate) {
        return baseMapper.selectByStockAndDateRange(code, startDate, endDate);
    }

    @Override
    @Cacheable(key = "'byType:' + #type + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<InfoFiling> getByType(String type, int limit) {
        return baseMapper.selectByType(type, limit);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoFiling entity) {
        return super.save(entity);
    }
}
