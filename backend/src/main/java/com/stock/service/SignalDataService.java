package com.stock.service;

import com.stock.entity.*;
import java.util.List;
import java.util.Map;

/**
 * 信号数据服务 — 题材、龙虎榜、北向资金、解禁、行业对比等读密集型查询
 */
public interface SignalDataService {

    // ==================== 题材热点 ====================
    Map<String, Object> getHotReason(String date);
    List<String> getHotReasonDates();

    // ==================== 龙虎榜 ====================
    Map<String, Object> getDragonTigerDaily(String date);
    List<SignalDragonTigerDetail> getDragonTigerByStock(String code);
    SignalDragonTigerDetail getDragonTigerDetail(String date, String code);
    List<String> getDragonTigerDates();

    // ==================== 北向资金 ====================
    List<SignalNorthbound> getNorthboundLatest(int days);
    SignalNorthbound getNorthboundByDate(String date);
    List<String> getNorthboundDates();

    // ==================== 限售解禁 ====================
    List<SignalLockupDetail> getLockupByStock(String code);
    List<SignalLockupDetail> getUpcomingLockup();
    List<SignalLockupDetail> getLockupHistory();

    // ==================== 行业排行 ====================
    Map<String, Object> getIndustryCompare(String date);
    List<String> getIndustryDates();

    // ==================== 概念板块 ====================
    List<SignalConceptBlock> getConceptBlocks(String code);
    List<SignalConceptBlock> getConceptBlocksByType(String code, String type);

    // ==================== 资金流向 ====================
    List<SignalFundFlow> getFundFlow(String code, int limit);
    List<SignalFundFlow> getFundFlowSince(String code, String since);

    // ==================== 龙虎榜明细 ====================
    Map<String, Object> getDragonTigerDetailByDate(String date);
    List<SignalDragonTigerDetail> getDragonTigerDetailByStock(String code);
    List<String> getDragonTigerDetailDates();

    // ==================== 解禁明细 ====================
    List<SignalLockupDetail> getLockupDetailByStock(String code);
    List<SignalLockupDetail> getUpcomingLockups(int limit);
    List<SignalLockupDetail> getLockupByTag(String code, String tag);
}
