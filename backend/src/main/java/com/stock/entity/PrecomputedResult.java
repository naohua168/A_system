package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("precomputed_yearly_return")
public class PrecomputedResult {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private Integer year;

    private BigDecimal yearlyReturn;

    private Integer rank;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
