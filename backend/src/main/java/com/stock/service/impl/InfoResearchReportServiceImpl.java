package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoResearchReport;
import com.stock.mapper.InfoResearchReportMapper;
import com.stock.service.InfoResearchReportService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoResearchReport")
public class InfoResearchReportServiceImpl extends ServiceImpl<InfoResearchReportMapper, InfoResearchReport>
        implements InfoResearchReportService {

    @Override
    @Cacheable(key = "'byStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<InfoResearchReport> getByStock(String code) {
        return baseMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'byRange:' + #code + ':' + #startDate + ':' + #endDate", unless = "#result == null || #result.isEmpty()")
    public List<InfoResearchReport> getByStockAndDateRange(String code, String startDate, String endDate) {
        return baseMapper.selectByStockAndDateRange(code, startDate, endDate);
    }

    @Override
    @Cacheable(key = "'byOrg:' + #org + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<InfoResearchReport> getByOrg(String org, int limit) {
        return baseMapper.selectByOrg(org, limit);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoResearchReport entity) {
        return super.save(entity);
    }
}
