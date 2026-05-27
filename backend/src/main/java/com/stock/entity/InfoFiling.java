package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 资讯层 — 巨潮公告
 * 数据源: akshare stock_zh_a_disclosure_report_cninfo
 * 从 a-stock-data 公告层迁移合并
 * 注: publishDate/filingType字段名匹配DB兼容列, @JsonProperty控制JSON序列化名
 */
@Data
@TableName("info_filing")
public class InfoFiling {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private String stockName;

    private String title;

    @TableField("filing_date")
    @JsonProperty("filingDate")
    private String publishDate;

    @TableField("category")
    @JsonProperty("category")
    private String filingType;

    private String url;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
