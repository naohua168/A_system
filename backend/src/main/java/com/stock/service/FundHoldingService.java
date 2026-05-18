package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.FundHolding;

import java.util.List;

public interface FundHoldingService extends IService<FundHolding> {
    List<FundHolding> getTopHoldings(String fundCode, int limit);
}
