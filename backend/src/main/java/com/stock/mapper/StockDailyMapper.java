package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.StockDaily;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface StockDailyMapper extends BaseMapper<StockDaily> {

    /** 查询某年第一个交易日 */
    StockDaily selectFirstOfYear(@Param("stockCode") String stockCode,
                                  @Param("year") int year);

    /** 查询某年最后一个交易日 */
    StockDaily selectLastOfYear(@Param("stockCode") String stockCode,
                                 @Param("year") int year);

    /** 按日期范围查询 */
    List<StockDaily> selectByDateRange(@Param("stockCode") String stockCode,
                                        @Param("startDate") String startDate,
                                        @Param("endDate") String endDate);

    /** 多条件筛选股票 */
    List<Map<String, Object>> selectStocksByFilter(@Param("industry") String industry,
                                                    @Param("minPrice") BigDecimal minPrice,
                                                    @Param("maxPrice") BigDecimal maxPrice,
                                                    @Param("minChange") BigDecimal minChange,
                                                    @Param("limit") int limit);

    /** 行业涨跌排行 */
    List<Map<String, Object>> selectSectorRanking(@Param("tradeDate") String tradeDate);

    /** 行业分层云图（一级行业 + 成分股明细） */
    List<Map<String, Object>> selectIndustryTreeMap(@Param("tradeDate") String tradeDate);

    /** 查询最大交易日（即最近有数据的一天） */
    String selectMaxTradeDate();

    /** 查询带最新行情数据的股票列表 */
    List<Map<String, Object>> selectStocksWithPrice(@Param("keyword") String keyword,
                                                     @Param("industry") String industry,
                                                     @Param("market") String market,
                                                     @Param("limit") int limit,
                                                     @Param("offset") int offset,
                                                     @Param("sortField") String sortField,
                                                     @Param("sortOrder") String sortOrder);

    /** 板块K线聚合（按行业成分股每日均价计算） */
    List<Map<String, Object>> selectSectorKline(@Param("industry") String industry,
                                                 @Param("days") int days);
}
