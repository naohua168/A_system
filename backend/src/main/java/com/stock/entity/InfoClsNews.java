package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 资讯层 — 财联社快讯（分钟级电报）
 * 数据源: akshare stock_info_global_cls
 * 从 a-stock-data 新闻层迁移合并
 */
@Data
@TableName("info_cls_news")
public class InfoClsNews {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String title;

    private String publishTime;

    @TableField("`content`")
    private String content;

    private String source;

    private String url;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
