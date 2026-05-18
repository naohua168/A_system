package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.InfoConsensusEps;
import com.stock.mapper.InfoConsensusEpsMapper;
import com.stock.service.InfoConsensusEpsService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "infoConsensusEps")
public class InfoConsensusEpsServiceImpl extends ServiceImpl<InfoConsensusEpsMapper, InfoConsensusEps>
        implements InfoConsensusEpsService {

    @Override
    @Cacheable(key = "'byStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<InfoConsensusEps> getByStock(String code) {
        return baseMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'byStockYear:' + #code + ':' + #year", unless = "#result == null")
    public InfoConsensusEps getByStockAndYear(String code, String year) {
        return baseMapper.selectByStockAndYear(code, year);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(InfoConsensusEps entity) {
        return super.save(entity);
    }
}
