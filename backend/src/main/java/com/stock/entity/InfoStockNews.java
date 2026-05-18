package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 资讯层 — 个股新闻（东财源）
 * 数据源: akshare stock_news_em
 * 从 a-stock-data 新闻层迁移合并
 */
@Data
@TableName("info_stock_news")
public class InfoStockNews {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private String title;

    private String publishTime;

    private String contentSummary;

    private String source;

    private String url;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
