package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoResearchReport;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoResearchReportMapper extends BaseMapper<InfoResearchReport> {

    @Select("SELECT * FROM info_research_report WHERE stock_code = #{code} ORDER BY publish_date DESC")
    List<InfoResearchReport> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM info_research_report WHERE stock_code = #{code} AND publish_date BETWEEN #{startDate} AND #{endDate} ORDER BY publish_date DESC")
    List<InfoResearchReport> selectByStockAndDateRange(@Param("code") String code,
                                                        @Param("startDate") String startDate,
                                                        @Param("endDate") String endDate);

    @Select("SELECT * FROM info_research_report WHERE org_name LIKE CONCAT('%', #{org}, '%') ORDER BY publish_date DESC LIMIT #{limit}")
    List<InfoResearchReport> selectByOrg(@Param("org") String org, @Param("limit") int limit);

    @Select("SELECT DISTINCT stock_code FROM info_research_report ORDER BY stock_code")
    List<String> selectAvailableStocks();
}
