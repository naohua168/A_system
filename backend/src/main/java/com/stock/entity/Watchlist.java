package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("watchlist")
public class Watchlist {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private Integer assetType;

    private String assetCode;

    private String remark;

    private Integer sortOrder;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
