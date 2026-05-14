package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.FundNav;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface FundNavMapper extends BaseMapper<FundNav> {

    /** 净值走势查询 */
    List<FundNav> selectNavTrend(@Param("fundCode") String fundCode,
                                  @Param("startDate") String startDate,
                                  @Param("endDate") String endDate);

    /** 查询最新净值 */
    FundNav selectLatestNav(@Param("fundCode") String fundCode);

    /** 查询某时间点附近净值 */
    FundNav selectNavByDate(@Param("fundCode") String fundCode,
                             @Param("date") String date);
}
