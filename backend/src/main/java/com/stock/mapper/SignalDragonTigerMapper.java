package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalDragonTiger;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface SignalDragonTigerMapper extends BaseMapper<SignalDragonTiger> {

    @Select("SELECT * FROM signal_dragon_tiger WHERE trade_date = #{date} ORDER BY net_buy_wan DESC")
    List<SignalDragonTiger> selectDailyByDate(@Param("date") String date);

    @Select("SELECT * FROM signal_dragon_tiger WHERE stock_code = #{code} ORDER BY trade_date DESC LIMIT 30")
    List<SignalDragonTiger> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM signal_dragon_tiger WHERE trade_date = #{date} AND stock_code = #{code} LIMIT 1")
    SignalDragonTiger selectByDateAndStock(@Param("date") String date, @Param("code") String code);

    @Select("SELECT DISTINCT trade_date FROM signal_dragon_tiger ORDER BY trade_date DESC LIMIT 10")
    List<String> selectAvailableDates();

    /** 按日期范围查询龙虎榜，按净买入金额排序 */
    List<SignalDragonTiger> selectByDateRange(@Param("startDate") String startDate,
                                               @Param("endDate") String endDate,
                                               @Param("limit") Integer limit);

    /** 席位统计分析 */
    List<Map<String, Object>> selectSeatAnalysis(@Param("startDate") String startDate,
                                                  @Param("endDate") String endDate);
}
