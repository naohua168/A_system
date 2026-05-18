package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoReportPdf;
import com.stock.mapper.InfoReportPdfMapper;
import com.stock.service.InfoReportPdfService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoReportPdf")
public class InfoReportPdfServiceImpl extends ServiceImpl<InfoReportPdfMapper, InfoReportPdf>
        implements InfoReportPdfService {

    @Override
    @Cacheable(key = "'byStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<InfoReportPdf> getByStock(String code) {
        return baseMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'byReport:' + #reportId", unless = "#result == null")
    public InfoReportPdf getByReportId(Long reportId) {
        return baseMapper.selectByReportId(reportId);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoReportPdf entity) {
        return super.save(entity);
    }
}
