package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.FundNav;

import java.util.List;

public interface FundNavService extends IService<FundNav> {
    List<FundNav> getLatest(String fundCode, int days);
}
