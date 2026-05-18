package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("signal_concept_block")
public class SignalConceptBlock {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String stockCode;
    private String blockType;
    private String blockName;
    private String changePct;
    private String description;
    private String source;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
