package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoFiling;

import java.util.List;

public interface InfoFilingService extends IService<InfoFiling> {
    List<InfoFiling> getByStock(String code, int limit);
    List<InfoFiling> getByStockAndDateRange(String code, String startDate, String endDate);
    List<InfoFiling> getByType(String type, int limit);
}
