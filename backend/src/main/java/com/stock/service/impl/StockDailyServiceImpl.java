package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.StockDaily;
import com.stock.mapper.StockDailyMapper;
import com.stock.service.StockDailyService;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;

@Service
public class StockDailyServiceImpl extends ServiceImpl<StockDailyMapper, StockDaily> implements StockDailyService {

    @Override
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

    @Override
    public List<StockDaily> getLatestDays(String stockCode, int days) {
        LambdaQueryWrapper<StockDaily> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(StockDaily::getStockCode, stockCode);
        wrapper.orderByDesc(StockDaily::getTradeDate);
        wrapper.last("LIMIT " + days);
        List<StockDaily> list = baseMapper.selectList(wrapper);
        java.util.Collections.reverse(list);
        return list;
    }
}
