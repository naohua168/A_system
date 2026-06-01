package com.stock.service.impl;

import com.stock.entity.*;
import com.stock.mapper.*;
import com.stock.service.SignalDataService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.Caching;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Service
public class SignalDataServiceImpl implements SignalDataService {

    private static final Logger log = LoggerFactory.getLogger(SignalDataServiceImpl.class);

    private final SignalHotReasonMapper hotReasonMapper;
    private final SignalNorthboundMapper northboundMapper;
    private final SignalDailyIndustryMapper industryMapper;
    private final SignalConceptBlockMapper conceptBlockMapper;
    private final SignalFundFlowMapper fundFlowMapper;
    private final SignalDragonTigerDetailMapper dragonTigerDetailMapper;
    private final SignalLockupDetailMapper lockupDetailMapper;

    public SignalDataServiceImpl(
            SignalHotReasonMapper hotReasonMapper,
            SignalNorthboundMapper northboundMapper,
            SignalDailyIndustryMapper industryMapper,
            SignalConceptBlockMapper conceptBlockMapper,
            SignalFundFlowMapper fundFlowMapper,
            SignalDragonTigerDetailMapper dragonTigerDetailMapper,
            SignalLockupDetailMapper lockupDetailMapper) {
        this.hotReasonMapper = hotReasonMapper;
        this.northboundMapper = northboundMapper;
        this.industryMapper = industryMapper;
        this.conceptBlockMapper = conceptBlockMapper;
        this.fundFlowMapper = fundFlowMapper;
        this.dragonTigerDetailMapper = dragonTigerDetailMapper;
        this.lockupDetailMapper = lockupDetailMapper;
    }

    // ======================== 热点题材（signalHotData — TTL 5分钟） ========================

    @Override
    @Cacheable(cacheNames = "signalHotData", key = "'hotReason:' + #date", unless = "#result == null")
    public Map<String, Object> getHotReason(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalHotReason> list = hotReasonMapper.selectByDate(targetDate);
        if (list.isEmpty()) {
            return Map.of("date", targetDate, "records", list, "note", "当日无强势股数据，盘后15:30后更新");
        }
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(cacheNames = "signalHotData", key = "'hotReasonDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getHotReasonDates() {
        return hotReasonMapper.selectAvailableDates();
    }

    // ======================== 龙虎榜（signalDragonTiger — TTL 5分钟） ========================

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerDaily:' + #date", unless = "#result == null")
    public Map<String, Object> getDragonTigerDaily(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDragonTigerDetail> list = dragonTigerDetailMapper.selectByDate(targetDate);
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalDragonTigerDetail> getDragonTigerByStock(String code) {
        return dragonTigerDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerDetail:' + #date + ':' + #code", unless = "#result == null")
    public SignalDragonTigerDetail getDragonTigerDetail(String date, String code) {
        return dragonTigerDetailMapper.selectByDateAndStock(date, code);
    }

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getDragonTigerDates() {
        return dragonTigerDetailMapper.selectAvailableDates();
    }

    // ======================== 北向资金/资金流向（signalMarketData — TTL 30秒） ========================

    @Override
    @Cacheable(cacheNames = "signalMarketData", key = "'northboundLatest:' + #days", unless = "#result == null || #result.isEmpty()")
    public List<SignalNorthbound> getNorthboundLatest(int days) {
        return northboundMapper.selectLatest(days);
    }

    @Override
    @Cacheable(cacheNames = "signalMarketData", key = "'northboundByDate:' + #date", unless = "#result == null")
    public SignalNorthbound getNorthboundByDate(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        return northboundMapper.selectByDate(targetDate);
    }

    @Override
    @Cacheable(cacheNames = "signalMarketData", key = "'northboundDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getNorthboundDates() {
        return northboundMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(cacheNames = "signalMarketData", key = "'fundFlow:' + #code + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<SignalFundFlow> getFundFlow(String code, int limit) {
        return fundFlowMapper.selectByStock(code, limit);
    }

    @Override
    @Cacheable(cacheNames = "signalMarketData", key = "'fundFlowSince:' + #code + ':' + #since", unless = "#result == null || #result.isEmpty()")
    public List<SignalFundFlow> getFundFlowSince(String code, String since) {
        return fundFlowMapper.selectByStockSince(code, since);
    }

    // ======================== 解禁/行业比较（signalReferenceData — TTL 15分钟） ========================

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'lockupByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupByStock(String code) {
        return lockupDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'lockupUpcoming'", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getUpcomingLockup() {
        return lockupDetailMapper.selectUpcoming(30);
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'lockupHistory'", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupHistory() {
        return lockupDetailMapper.selectByTag("history", 30);
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'industryCompare:' + #date", unless = "#result == null")
    public Map<String, Object> getIndustryCompare(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDailyIndustry> list = industryMapper.selectByDate(targetDate);
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'industryDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getIndustryDates() {
        return industryMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'conceptBlocks:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalConceptBlock> getConceptBlocks(String code) {
        return conceptBlockMapper.selectByStock(code);
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'conceptBlocks:' + #code + ':' + #type", unless = "#result == null || #result.isEmpty()")
    public List<SignalConceptBlock> getConceptBlocksByType(String code, String type) {
        return conceptBlockMapper.selectByStockAndType(code, type);
    }

    // ======================== 龙虎榜明细（signalDragonTiger — TTL 5分钟） ========================

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerDetailByDate:' + #date", unless = "#result == null")
    public Map<String, Object> getDragonTigerDetailByDate(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDragonTigerDetail> list = dragonTigerDetailMapper.selectByDate(targetDate);
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerDetailByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalDragonTigerDetail> getDragonTigerDetailByStock(String code) {
        return dragonTigerDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(cacheNames = "signalDragonTiger", key = "'dragonTigerDetailDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getDragonTigerDetailDates() {
        return dragonTigerDetailMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'lockupDetailByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupDetailByStock(String code) {
        return lockupDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'lockupDetailUpcoming:' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getUpcomingLockups(int limit) {
        return lockupDetailMapper.selectUpcoming(limit);
    }

    @Override
    @Cacheable(cacheNames = "signalReferenceData", key = "'lockupDetailByTag:' + #code + ':' + #tag", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupByTag(String code, String tag) {
        return lockupDetailMapper.selectByStockAndTag(code, tag);
    }

    /**
     * 清空信号数据缓存（每日盘后数据刷新时调用）
     */
    @Caching(evict = {
            @CacheEvict(cacheNames = "signalHotData", allEntries = true),
            @CacheEvict(cacheNames = "signalDragonTiger", allEntries = true),
            @CacheEvict(cacheNames = "signalMarketData", allEntries = true),
            @CacheEvict(cacheNames = "signalReferenceData", allEntries = true),
    })
    public void clearCache() {
        log.info("信号数据缓存已清空");
    }
}
