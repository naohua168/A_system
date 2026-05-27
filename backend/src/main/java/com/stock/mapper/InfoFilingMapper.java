package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoFiling;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoFilingMapper extends BaseMapper<InfoFiling> {

    @Select("SELECT * FROM info_filing WHERE stock_code = #{code} ORDER BY filing_date DESC LIMIT #{limit}")
    List<InfoFiling> selectByStock(@Param("code") String code, @Param("limit") int limit);

    @Select("SELECT * FROM info_filing WHERE stock_code = #{code} AND filing_date BETWEEN #{startDate} AND #{endDate} ORDER BY filing_date DESC")
    List<InfoFiling> selectByStockAndDateRange(@Param("code") String code,
                                                @Param("startDate") String startDate,
                                                @Param("endDate") String endDate);

    @Select("SELECT * FROM info_filing WHERE category LIKE CONCAT('%', #{type}, '%') ORDER BY filing_date DESC LIMIT #{limit}")
    List<InfoFiling> selectByType(@Param("type") String type, @Param("limit") int limit);
}
