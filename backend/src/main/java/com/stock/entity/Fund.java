package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("fund")
public class Fund {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String fundCode;

    private String fundName;

    private String fundType;

    private String company;

    private String manager;

    private LocalDate establishDate;

    private BigDecimal nav;

    private BigDecimal accumulatedNav;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}
