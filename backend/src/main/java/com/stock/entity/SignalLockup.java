package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("signal_lockup")
public class SignalLockup {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String stockCode;
    private LocalDate lockupDate;
    private String lockupType;
    private BigDecimal shares;
    private BigDecimal floatRatio;
    private Integer isUpcoming;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
