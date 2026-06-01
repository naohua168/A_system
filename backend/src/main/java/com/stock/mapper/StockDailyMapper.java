package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.StockDaily;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface StockDailyMapper extends BaseMapper<StockDaily> {

    /** 查询某年第一个交易日（供 AnalysisService 使用） */
    StockDaily selectFirstOfYear(@Param("stockCode") String stockCode,
                                  @Param("year") int year);

    /** 查询某年最后一个交易日（供 AnalysisService 使用） */
    StockDaily selectLastOfYear(@Param("stockCode") String stockCode,
                                 @Param("year") int year);

    /** 按日期范围查询（供 AnalysisService 使用） */
    List<StockDaily> selectByDateRange(@Param("stockCode") String stockCode,
                                        @Param("startDate") String startDate,
                                        @Param("endDate") String endDate);
}
