package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_chat")
public class AiChat {
    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String sessionId;

    private Integer role;

    private String content;

    private String assetCode;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
