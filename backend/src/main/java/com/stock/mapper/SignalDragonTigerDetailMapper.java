package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalDragonTigerDetail;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SignalDragonTigerDetailMapper extends BaseMapper<SignalDragonTigerDetail> {

    @Select("SELECT * FROM signal_dragon_tiger_detail WHERE trade_date = #{date} ORDER BY net_buy_wan DESC")
    List<SignalDragonTigerDetail> selectByDate(@Param("date") String date);

    @Select("SELECT * FROM signal_dragon_tiger_detail WHERE stock_code = #{code} ORDER BY trade_date DESC LIMIT 50")
    List<SignalDragonTigerDetail> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM signal_dragon_tiger_detail WHERE trade_date = #{date} AND stock_code = #{code} LIMIT 1")
    SignalDragonTigerDetail selectByDateAndStock(@Param("date") String date, @Param("code") String code);

    @Select("SELECT DISTINCT trade_date FROM signal_dragon_tiger_detail ORDER BY trade_date DESC LIMIT 10")
    List<String> selectAvailableDates();
}
