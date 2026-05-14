package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalDailyIndustry;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface SignalDailyIndustryMapper extends BaseMapper<SignalDailyIndustry> {

    @Select("SELECT * FROM signal_daily_industry WHERE trade_date = #{date} ORDER BY rank_num ASC")
    List<SignalDailyIndustry> selectByDate(@Param("date") String date);

    @Select("SELECT DISTINCT trade_date FROM signal_daily_industry ORDER BY trade_date DESC LIMIT 10")
    List<String> selectAvailableDates();

    /** 行业排行统计（多日汇总） */
    List<Map<String, Object>> selectIndustryRankingStats(@Param("startDate") String startDate,
                                                          @Param("endDate") String endDate);

    /** 日期范围内某行业每日走势 */
    List<Map<String, Object>> selectIndustryTrend(@Param("industryName") String industryName,
                                                   @Param("startDate") String startDate,
                                                   @Param("endDate") String endDate);
}
