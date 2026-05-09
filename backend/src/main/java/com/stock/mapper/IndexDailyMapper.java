package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.IndexDaily;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface IndexDailyMapper extends BaseMapper<IndexDaily> {

    /** 查询指定指数的K线数据 */
    @Select("SELECT * FROM index_daily WHERE index_code = #{indexCode} ORDER BY trade_date DESC LIMIT #{limit}")
    List<IndexDaily> selectRecent(@Param("indexCode") String indexCode, @Param("limit") int limit);

    /** 查询指定日期范围的K线 */
    @Select("SELECT * FROM index_daily WHERE index_code = #{indexCode} AND trade_date >= #{startDate} AND trade_date <= #{endDate} ORDER BY trade_date ASC")
    List<IndexDaily> selectByDateRange(@Param("indexCode") String indexCode,
                                        @Param("startDate") String startDate,
                                        @Param("endDate") String endDate);

    /** 查询最近交易日 */
    @Select("SELECT MAX(trade_date) FROM index_daily")
    String selectMaxTradeDate();

    /** 查询行业/市场排行（用指数涨跌幅）
     *  返回每个指数最新一条数据 */
    @Select("SELECT i.index_code AS indexCode, i.index_name AS indexName, i.category, " +
            "d.close_point AS closePoint, d.change_percent AS changePercent, d.trade_date AS tradeDate " +
            "FROM market_index i " +
            "JOIN index_daily d ON i.index_code = d.index_code " +
            "WHERE d.trade_date = (SELECT MAX(trade_date) FROM index_daily) " +
            "ORDER BY d.change_percent DESC")
    List<Map<String, Object>> selectIndexRanking();
}
