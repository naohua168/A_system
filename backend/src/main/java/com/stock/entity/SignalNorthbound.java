package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("signal_northbound")
public class SignalNorthbound {
    @TableId(type = IdType.AUTO)
    private Long id;
    private LocalDate tradeDate;
    private BigDecimal hgtYi;
    private BigDecimal sgtYi;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
