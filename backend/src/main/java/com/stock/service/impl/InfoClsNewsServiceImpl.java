package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoClsNews;
import com.stock.mapper.InfoClsNewsMapper;
import com.stock.service.InfoClsNewsService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoClsNews")
public class InfoClsNewsServiceImpl extends ServiceImpl<InfoClsNewsMapper, InfoClsNews>
        implements InfoClsNewsService {

    @Override
    @Cacheable(key = "'latest:' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<InfoClsNews> getLatest(int limit) {
        return baseMapper.selectLatest(limit);
    }

    @Override
    @Cacheable(key = "'since:' + #since", unless = "#result == null || #result.isEmpty()")
    public List<InfoClsNews> getSince(String since) {
        return baseMapper.selectSince(since);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoClsNews entity) {
        return super.save(entity);
    }
}
