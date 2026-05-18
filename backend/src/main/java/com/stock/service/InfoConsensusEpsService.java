package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoConsensusEps;

import java.util.List;

public interface InfoConsensusEpsService extends IService<InfoConsensusEps> {
    List<InfoConsensusEps> getByStock(String code);
    InfoConsensusEps getByStockAndYear(String code, String year);
}
