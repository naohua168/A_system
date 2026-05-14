package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalHotReason;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SignalHotReasonMapper extends BaseMapper<SignalHotReason> {

    @Select("SELECT * FROM signal_hot_reason WHERE trade_date = #{date} ORDER BY change_pct DESC")
    List<SignalHotReason> selectByDate(@Param("date") String date);

    @Select("SELECT DISTINCT trade_date FROM signal_hot_reason ORDER BY trade_date DESC LIMIT 10")
    List<String> selectAvailableDates();

    /** 日期范围查询，按涨幅排序分页 */
    List<SignalHotReason> selectByDateRange(@Param("startDate") String startDate,
                                             @Param("endDate") String endDate,
                                             @Param("limit") int limit,
                                             @Param("offset") int offset);

    /** 查询日期范围内的总数 */
    long countByDateRange(@Param("startDate") String startDate,
                           @Param("endDate") String endDate);
}
