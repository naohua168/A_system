package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("fund_holding")
public class FundHolding {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String fundCode;

    private String stockCode;

    private String stockName;

    private BigDecimal ratio;

    private Integer rankNum;

    private LocalDate reportDate;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
