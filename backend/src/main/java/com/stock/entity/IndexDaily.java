package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@TableName("index_daily")
public class IndexDaily {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String indexCode;
    private LocalDate tradeDate;
    private BigDecimal openPoint;
    private BigDecimal highPoint;
    private BigDecimal lowPoint;
    private BigDecimal closePoint;
    private BigDecimal preClose;
    private Long volume;
    private BigDecimal amount;
    private BigDecimal changePercent;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getIndexCode() { return indexCode; }
    public void setIndexCode(String indexCode) { this.indexCode = indexCode; }
    public LocalDate getTradeDate() { return tradeDate; }
    public void setTradeDate(LocalDate tradeDate) { this.tradeDate = tradeDate; }
    public BigDecimal getOpenPoint() { return openPoint; }
    public void setOpenPoint(BigDecimal openPoint) { this.openPoint = openPoint; }
    public BigDecimal getHighPoint() { return highPoint; }
    public void setHighPoint(BigDecimal highPoint) { this.highPoint = highPoint; }
    public BigDecimal getLowPoint() { return lowPoint; }
    public void setLowPoint(BigDecimal lowPoint) { this.lowPoint = lowPoint; }
    public BigDecimal getClosePoint() { return closePoint; }
    public void setClosePoint(BigDecimal closePoint) { this.closePoint = closePoint; }
    public BigDecimal getPreClose() { return preClose; }
    public void setPreClose(BigDecimal preClose) { this.preClose = preClose; }
    public Long getVolume() { return volume; }
    public void setVolume(Long volume) { this.volume = volume; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public BigDecimal getChangePercent() { return changePercent; }
    public void setChangePercent(BigDecimal changePercent) { this.changePercent = changePercent; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
