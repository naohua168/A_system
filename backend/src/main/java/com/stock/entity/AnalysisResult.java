package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("analysis_result")
public class AnalysisResult {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Integer assetType;

    private String assetCode;

    private String analysisType;

    private String resultJson;

    private String summary;

    private LocalDate analysisDate;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
