package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.AnalysisResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface AnalysisResultMapper extends BaseMapper<AnalysisResult> {

    /** 按类型查询 */
    List<AnalysisResult> selectByType(@Param("analysisType") String analysisType,
                                      @Param("limit") Integer limit);

    /** 按时间范围查询 */
    List<AnalysisResult> selectByTimeRange(@Param("startDate") String startDate,
                                            @Param("endDate") String endDate,
                                            @Param("analysisType") String analysisType,
                                            @Param("assetType") Integer assetType);

    /** 按资产编码查询最新结果 */
    AnalysisResult selectLatestByAsset(@Param("assetCode") String assetCode,
                                       @Param("analysisType") String analysisType);
}
