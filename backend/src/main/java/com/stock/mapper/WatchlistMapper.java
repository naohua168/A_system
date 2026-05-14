package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.Watchlist;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

@Mapper
public interface WatchlistMapper extends BaseMapper<Watchlist> {

    /** 自选股详情JOIN查询（股票） */
    List<Map<String, Object>> selectStockDetail(@Param("userId") Long userId);

    /** 自选股详情JOIN查询（基金） */
    List<Map<String, Object>> selectFundDetail(@Param("userId") Long userId);

    /** 自选股全部详情 */
    List<Map<String, Object>> selectAllDetail(@Param("userId") Long userId);
}
