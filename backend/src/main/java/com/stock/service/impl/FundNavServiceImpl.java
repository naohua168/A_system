package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.FundNav;
import com.stock.mapper.FundNavMapper;
import com.stock.service.FundNavService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
@CacheConfig(cacheNames = "fundNav")
public class FundNavServiceImpl extends ServiceImpl<FundNavMapper, FundNav> implements FundNavService {

    @Override
    @Cacheable(key = "'latest:' + #fundCode + ':' + #days", unless = "#result == null || #result.isEmpty()")
    public List<FundNav> getLatest(String fundCode, int days) {
        LambdaQueryWrapper<FundNav> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FundNav::getFundCode, fundCode);
        wrapper.orderByDesc(FundNav::getNavDate);
        wrapper.last("LIMIT " + days);
        List<FundNav> list = baseMapper.selectList(wrapper);
        Collections.reverse(list);
        return list;
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(FundNav entity) {
        return super.save(entity);
    }
}
