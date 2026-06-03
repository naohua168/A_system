package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.StockDaily;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

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

    /** 股票筛选（供 AnalysisService 使用） */
    @Select("SELECT * FROM stock_daily WHERE 1=0")
    List<Map<String, Object>> selectStocksByFilter(@Param("industry") String industry,
                                                    @Param("minPrice") BigDecimal minPrice,
                                                    @Param("maxPrice") BigDecimal maxPrice,
                                                    @Param("minChange") BigDecimal minChange,
                                                    @Param("limit") Integer limit);

    /** 行业排行（供 AnalysisService 使用） */
    @Select("SELECT * FROM stock_daily WHERE 1=0")
    List<Map<String, Object>> selectSectorRanking(@Param("tradeDate") String tradeDate);

    /** 最大交易日期（供 AnalysisService 使用） */
    @Select("SELECT MAX(trade_date) FROM stock_daily")
    String selectMaxTradeDate();
}
