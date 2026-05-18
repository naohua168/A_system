package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoReportPdf;

import java.util.List;

public interface InfoReportPdfService extends IService<InfoReportPdf> {
    List<InfoReportPdf> getByStock(String code);
    InfoReportPdf getByReportId(Long reportId);
}
