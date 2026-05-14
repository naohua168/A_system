package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalNorthbound;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface SignalNorthboundMapper extends BaseMapper<SignalNorthbound> {

    @Select("SELECT * FROM signal_northbound WHERE trade_date = #{date} LIMIT 1")
    SignalNorthbound selectByDate(@Param("date") String date);

    @Select("SELECT * FROM signal_northbound ORDER BY trade_date DESC LIMIT #{limit}")
    List<SignalNorthbound> selectLatest(@Param("limit") int limit);

    @Select("SELECT DISTINCT trade_date FROM signal_northbound ORDER BY trade_date DESC LIMIT 10")
    List<String> selectAvailableDates();

    /** 时间段汇总 */
    Map<String, Object> selectPeriodSummary(@Param("startDate") String startDate,
                                             @Param("endDate") String endDate);

    /** 日均净流入统计（按月份分组） */
    List<Map<String, Object>> selectMonthlyAvgInflow(@Param("startDate") String startDate,
                                                      @Param("endDate") String endDate);
}
