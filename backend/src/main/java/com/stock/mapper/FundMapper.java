package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.Fund;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface FundMapper extends BaseMapper<Fund> {
}
