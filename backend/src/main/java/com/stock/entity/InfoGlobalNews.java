package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 资讯层 — 全球财经资讯
 * 数据源: akshare stock_info_global_em
 * 从 a-stock-data 新闻层迁移合并
 */
@Data
@TableName("info_global_news")
public class InfoGlobalNews {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String title;

    private String publishTime;

    private String summary;

    private String source;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
