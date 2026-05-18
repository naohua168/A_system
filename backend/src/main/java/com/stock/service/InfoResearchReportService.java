package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoResearchReport;

import java.util.List;

public interface InfoResearchReportService extends IService<InfoResearchReport> {
    List<InfoResearchReport> getByStock(String code);
    List<InfoResearchReport> getByStockAndDateRange(String code, String startDate, String endDate);
    List<InfoResearchReport> getByOrg(String org, int limit);
}
