package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 资讯层 — 机构一致预期EPS
 * 数据源: akshare (同花顺源)
 * 从 a-stock-data 研报层迁移合并
 */
@Data
@TableName("info_consensus_eps")
public class InfoConsensusEps {
    @TableId(type = IdType.AUTO)
    private Long id;

    private String stockCode;

    private String year;

    private Integer forecastCount;

    private BigDecimal minEps;

    private BigDecimal avgEps;

    private BigDecimal maxEps;

    private BigDecimal industryAvg;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
