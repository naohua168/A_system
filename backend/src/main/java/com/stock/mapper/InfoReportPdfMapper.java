package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoReportPdf;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoReportPdfMapper extends BaseMapper<InfoReportPdf> {

    @Select("SELECT * FROM info_report_pdf WHERE stock_code = #{code} ORDER BY created_at DESC LIMIT 50")
    List<InfoReportPdf> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM info_report_pdf WHERE report_id = #{reportId} LIMIT 1")
    InfoReportPdf selectByReportId(@Param("reportId") Long reportId);
}
