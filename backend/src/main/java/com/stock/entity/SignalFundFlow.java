package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("signal_fund_flow")
public class SignalFundFlow {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String stockCode;
    private String tradeDate;
    private BigDecimal close;
    private String changePct;
    private String superNetIn;
    private String largeNetIn;
    private String mediumNetIn;
    private String littleNetIn;
    private String mainIn;
    private String source;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
