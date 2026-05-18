package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoStockNews;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoStockNewsMapper extends BaseMapper<InfoStockNews> {

    @Select("SELECT * FROM info_stock_news WHERE stock_code = #{code} ORDER BY publish_time DESC LIMIT #{limit}")
    List<InfoStockNews> selectByStock(@Param("code") String code, @Param("limit") int limit);

    @Select("SELECT * FROM info_stock_news WHERE stock_code = #{code} AND publish_time >= #{since} ORDER BY publish_time DESC")
    List<InfoStockNews> selectByStockSince(@Param("code") String code, @Param("since") String since);
}
