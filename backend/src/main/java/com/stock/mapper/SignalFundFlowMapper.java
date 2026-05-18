package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalFundFlow;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SignalFundFlowMapper extends BaseMapper<SignalFundFlow> {

    @Select("SELECT * FROM signal_fund_flow WHERE stock_code = #{code} ORDER BY trade_date DESC LIMIT #{limit}")
    List<SignalFundFlow> selectByStock(@Param("code") String code, @Param("limit") int limit);

    @Select("SELECT * FROM signal_fund_flow WHERE stock_code = #{code} AND trade_date >= #{since} ORDER BY trade_date DESC")
    List<SignalFundFlow> selectByStockSince(@Param("code") String code, @Param("since") String since);
}
