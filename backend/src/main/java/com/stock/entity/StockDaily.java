package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("stock_daily")
public class StockDaily {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private LocalDate tradeDate;

    private BigDecimal openPrice;

    private BigDecimal highPrice;

    private BigDecimal lowPrice;

    private BigDecimal closePrice;

    private BigDecimal preClose;

    private Long volume;

    private BigDecimal amount;

    private BigDecimal changePercent;

    private BigDecimal turnoverRate;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
