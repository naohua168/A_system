package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoStockNews;

import java.util.List;

public interface InfoStockNewsService extends IService<InfoStockNews> {
    List<InfoStockNews> getByStock(String code, int limit);
    List<InfoStockNews> getByStockSince(String code, String since);
}
