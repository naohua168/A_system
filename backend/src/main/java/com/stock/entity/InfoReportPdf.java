package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 资讯层 — 研报PDF下载记录
 * 数据源: 东财PDF服务器
 * 从 a-stock-data 研报层迁移合并
 */
@Data
@TableName("info_report_pdf")
public class InfoReportPdf {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long reportId;

    private String stockCode;

    private String title;

    private String pdfPath;

    private Long fileSize;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
