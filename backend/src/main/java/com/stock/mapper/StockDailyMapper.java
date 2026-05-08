package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.StockDaily;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface StockDailyMapper extends BaseMapper<StockDaily> {
}
