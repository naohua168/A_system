package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("stock")
public class Stock {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private String stockName;

    private String market;

    private String industry;

    private LocalDate listingDate;

    private BigDecimal totalShares;

    private BigDecimal circulatedShares;

    private BigDecimal pe;

    private BigDecimal pb;

    private BigDecimal totalMarketCap;

    private BigDecimal floatMarketCap;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
