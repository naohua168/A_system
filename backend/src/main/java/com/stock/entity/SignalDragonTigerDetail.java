package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("signal_dragon_tiger_detail")
public class SignalDragonTigerDetail {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String tradeDate;
    private String stockCode;
    private String stockName;
    private String reason;
    private BigDecimal close;
    private BigDecimal changePct;
    private BigDecimal netBuyWan;
    private BigDecimal buyWan;
    private BigDecimal sellWan;
    private BigDecimal turnoverPct;
    private String source;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
