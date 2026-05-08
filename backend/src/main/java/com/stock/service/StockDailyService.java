package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.StockDaily;
import com.baomidou.mybatisplus.core.metadata.IPage;

import java.time.LocalDate;
import java.util.List;

public interface StockDailyService extends IService<StockDaily> {
    IPage<StockDaily> getKLineData(String stockCode, LocalDate startDate, LocalDate endDate, int page, int size);
    List<StockDaily> getLatestDays(String stockCode, int days);
}
