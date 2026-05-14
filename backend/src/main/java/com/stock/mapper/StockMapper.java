package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.Stock;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface StockMapper extends BaseMapper<Stock> {

    /** 多条件股票列表查询 */
    List<Map<String, Object>> selectByFilter(@Param("keyword") String keyword,
                                              @Param("industry") String industry,
                                              @Param("market") String market,
                                              @Param("minPrice") BigDecimal minPrice,
                                              @Param("maxPrice") BigDecimal maxPrice,
                                              @Param("minPe") BigDecimal minPe,
                                              @Param("maxPe") BigDecimal maxPe,
                                              @Param("sortField") String sortField,
                                              @Param("sortOrder") String sortOrder,
                                              @Param("limit") Integer limit,
                                              @Param("offset") Integer offset);

    /** 按行业统计 */
    List<Map<String, Object>> selectIndustryStats();

    /** 按市值排序查询 */
    List<Map<String, Object>> selectByMarketCap(@Param("minCap") BigDecimal minCap,
                                                 @Param("maxCap") BigDecimal maxCap,
                                                 @Param("limit") Integer limit);
}
