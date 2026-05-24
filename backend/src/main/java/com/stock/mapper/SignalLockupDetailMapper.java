package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalLockupDetail;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SignalLockupDetailMapper extends BaseMapper<SignalLockupDetail> {

    @Select("SELECT * FROM signal_lockup_detail WHERE stock_code = #{code} ORDER BY lockup_date DESC")
    List<SignalLockupDetail> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM signal_lockup_detail WHERE type_tag = 'upcoming' ORDER BY lockup_date ASC LIMIT #{limit}")
    List<SignalLockupDetail> selectUpcoming(@Param("limit") int limit);

    @Select("SELECT * FROM signal_lockup_detail WHERE stock_code = #{code} AND type_tag = #{tag} ORDER BY lockup_date DESC")
    List<SignalLockupDetail> selectByStockAndTag(@Param("code") String code, @Param("tag") String tag);

    @Select("SELECT * FROM signal_lockup_detail WHERE type_tag = #{tag} ORDER BY lockup_date DESC LIMIT #{limit}")
    List<SignalLockupDetail> selectByTag(@Param("tag") String tag, @Param("limit") int limit);
}
