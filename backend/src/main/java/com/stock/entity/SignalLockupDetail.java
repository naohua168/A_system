package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("signal_lockup_detail")
public class SignalLockupDetail {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String stockCode;
    private String lockupDate;
    private String lockupType;
    private BigDecimal shares;
    private String floatRatio;
    private String ratio;
    private String typeTag;
    private String source;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
