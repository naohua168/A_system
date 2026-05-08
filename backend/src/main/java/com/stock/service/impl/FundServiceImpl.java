package com.stock.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.Fund;
import com.stock.mapper.FundMapper;
import com.stock.service.FundService;
import org.springframework.stereotype.Service;

@Service
public class FundServiceImpl extends ServiceImpl<FundMapper, Fund> implements FundService {
}
