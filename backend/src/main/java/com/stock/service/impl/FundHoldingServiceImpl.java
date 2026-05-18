package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.FundHolding;
import com.stock.mapper.FundHoldingMapper;
import com.stock.service.FundHoldingService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@CacheConfig(cacheNames = "fundHolding")
public class FundHoldingServiceImpl extends ServiceImpl<FundHoldingMapper, FundHolding> implements FundHoldingService {

    @Override
    @Cacheable(key = "'top:' + #fundCode + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<FundHolding> getTopHoldings(String fundCode, int limit) {
        LambdaQueryWrapper<FundHolding> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FundHolding::getFundCode, fundCode);
        wrapper.orderByAsc(FundHolding::getRankNum);
        wrapper.last("LIMIT " + limit);
        return baseMapper.selectList(wrapper);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(FundHolding entity) {
        return super.save(entity);
    }
}
