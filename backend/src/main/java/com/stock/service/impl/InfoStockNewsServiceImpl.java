package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoStockNews;
import com.stock.mapper.InfoStockNewsMapper;
import com.stock.service.InfoStockNewsService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoStockNews")
public class InfoStockNewsServiceImpl extends ServiceImpl<InfoStockNewsMapper, InfoStockNews>
        implements InfoStockNewsService {

    @Override
    @Cacheable(key = "'byStock:' + #code + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<InfoStockNews> getByStock(String code, int limit) {
        return baseMapper.selectByStock(code, limit);
    }

    @Override
    @Cacheable(key = "'since:' + #code + ':' + #since", unless = "#result == null || #result.isEmpty()")
    public List<InfoStockNews> getByStockSince(String code, String since) {
        return baseMapper.selectByStockSince(code, since);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoStockNews entity) {
        return super.save(entity);
    }
}
