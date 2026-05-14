package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalLockup;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface SignalLockupMapper extends BaseMapper<SignalLockup> {

    @Select("SELECT * FROM signal_lockup WHERE stock_code = #{code} ORDER BY lockup_date ASC LIMIT 30")
    List<SignalLockup> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM signal_lockup WHERE is_upcoming = 1 ORDER BY lockup_date ASC LIMIT 30")
    List<SignalLockup> selectUpcoming();

    @Select("SELECT * FROM signal_lockup WHERE is_upcoming = 0 ORDER BY lockup_date DESC LIMIT 30")
    List<SignalLockup> selectHistory();

    /** 即将解禁查询（指定日期范围） */
    List<SignalLockup> selectUpcomingByDateRange(@Param("startDate") String startDate,
                                                  @Param("endDate") String endDate);

    /** 解禁规模排行 */
    List<Map<String, Object>> selectByScaleRanking(@Param("startDate") String startDate,
                                                    @Param("endDate") String endDate,
                                                    @Param("limit") Integer limit);
}
