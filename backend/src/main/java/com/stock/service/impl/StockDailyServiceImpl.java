package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.StockDaily;
import com.stock.mapper.StockDailyMapper;
import com.stock.service.StockDailyService;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;

@Service
@CacheConfig(cacheNames = "stockDaily")
public class StockDailyServiceImpl extends ServiceImpl<StockDailyMapper, StockDaily> implements StockDailyService {

    @Override
    @Cacheable(key = "'kline:' + #stockCode + ':' + #startDate + ':' + #endDate + ':' + #page + ':' + #size",
               unless = "#result == null")
    public IPage<StockDaily> getKLineData(String stockCode, LocalDate startDate, LocalDate endDate, int page, int size) {
        LambdaQueryWrapper<StockDaily> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(StockDaily::getStockCode, stockCode);
        if (startDate != null) {
            wrapper.ge(StockDaily::getTradeDate, startDate);
        }
        if (endDate != null) {
            wrapper.le(StockDaily::getTradeDate, endDate);
        }
        wrapper.orderByAsc(StockDaily::getTradeDate);
        return baseMapper.selectPage(new Page<>(page, size), wrapper);
    }

    /**
     * 获取某股票最近 N 天的K线数据
     * <p>
     * 使用 MyBatis-Plus Page 对象实现分页，
     * 替代字符串拼接 LIMIT，消除 SQL 注入风险。
     */
    @Override
    @Cacheable(key = "'latest:' + #stockCode + ':' + #days", unless = "#result == null || #result.isEmpty()")
    public List<StockDaily> getLatestDays(String stockCode, int days) {
        LambdaQueryWrapper<StockDaily> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(StockDaily::getStockCode, stockCode);
        wrapper.orderByDesc(StockDaily::getTradeDate);
        List<StockDaily> list = baseMapper.selectPage(new Page<>(1, days), wrapper).getRecords();
        java.util.Collections.reverse(list);
        return list;
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean save(StockDaily entity) {
        return super.save(entity);
    }

    @Override
    @CacheEvict(allEntries = true)
    public boolean updateById(StockDaily entity) {
        return super.updateById(entity);
    }
}
