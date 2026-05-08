package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("fund_nav")
public class FundNav {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String fundCode;

    private LocalDate navDate;

    private BigDecimal nav;

    private BigDecimal accumulatedNav;

    private BigDecimal dailyReturn;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
