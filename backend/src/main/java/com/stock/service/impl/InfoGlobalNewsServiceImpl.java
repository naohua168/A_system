package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoGlobalNews;
import com.stock.mapper.InfoGlobalNewsMapper;
import com.stock.service.InfoGlobalNewsService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoGlobalNews")
public class InfoGlobalNewsServiceImpl extends ServiceImpl<InfoGlobalNewsMapper, InfoGlobalNews>
        implements InfoGlobalNewsService {

    @Override
    @Cacheable(key = "'latest:' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<InfoGlobalNews> getLatest(int limit) {
        return baseMapper.selectLatest(limit);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoGlobalNews entity) {
        return super.save(entity);
    }
}
