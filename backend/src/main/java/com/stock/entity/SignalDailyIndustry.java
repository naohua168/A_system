package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("signal_daily_industry")
public class SignalDailyIndustry {
    @TableId(type = IdType.AUTO)
    private Long id;
    private LocalDate tradeDate;
    private Integer rankNum;
    private String industryName;
    private BigDecimal changePct;
    private BigDecimal turnoverYi;
    private BigDecimal netInflowYi;
    private Integer upCount;
    private Integer downCount;
    private String leader;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
