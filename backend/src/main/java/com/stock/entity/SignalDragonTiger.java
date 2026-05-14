package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("signal_dragon_tiger")
public class SignalDragonTiger {
    @TableId(type = IdType.AUTO)
    private Long id;
    private LocalDate tradeDate;
    private String stockCode;
    private String stockName;
    private String reason;
    private BigDecimal netBuyWan;
    private BigDecimal buyWan;
    private BigDecimal sellWan;
    private BigDecimal changePct;
    private BigDecimal turnoverPct;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
