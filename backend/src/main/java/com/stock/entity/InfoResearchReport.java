package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 资讯层 — 研报记录
 * 数据源: 东财 reportapi
 * 从 a-stock-data 研报层迁移合并
 */
@Data
@TableName("info_research_report")
public class InfoResearchReport {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private String title;

    private String publishDate;

    private String orgName;

    private String rating;

    private BigDecimal predictEpsThisYear;

    private BigDecimal predictEpsNextYear;

    private String infoCode;

    private String pageUrl;

    private String source;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
