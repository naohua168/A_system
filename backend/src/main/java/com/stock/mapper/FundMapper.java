package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.Fund;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface FundMapper extends BaseMapper<Fund> {

    /** 基金列表查询（带筛选条件） */
    List<Map<String, Object>> selectByFilter(@Param("fundType") String fundType,
                                              @Param("keyword") String keyword,
                                              @Param("company") String company,
                                              @Param("minScale") BigDecimal minScale,
                                              @Param("maxScale") BigDecimal maxScale,
                                              @Param("sortField") String sortField,
                                              @Param("sortOrder") String sortOrder,
                                              @Param("limit") Integer limit,
                                              @Param("offset") Integer offset);

    /** 基金类型列表 */
    List<String> selectFundTypes();
}
