package com.stock.service.impl;

import com.stock.entity.*;
import com.stock.mapper.*;
import com.stock.service.SignalDataService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.CacheConfig;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Service
@CacheConfig(cacheNames = "signalData")
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

    @Override
    @Cacheable(key = "'hotReason:' + #date", unless = "#result == null")
    public Map<String, Object> getHotReason(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalHotReason> list = hotReasonMapper.selectByDate(targetDate);
        if (list.isEmpty()) {
            return Map.of("date", targetDate, "records", list, "note", "当日无强势股数据，盘后15:30后更新");
        }
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(key = "'hotReasonDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getHotReasonDates() {
        return hotReasonMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(key = "'dragonTigerDaily:' + #date", unless = "#result == null")
    public Map<String, Object> getDragonTigerDaily(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDragonTigerDetail> list = dragonTigerDetailMapper.selectByDate(targetDate);
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(key = "'dragonTigerByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalDragonTigerDetail> getDragonTigerByStock(String code) {
        return dragonTigerDetailMapper.selectByStock(code);
    }

    @Override
    public SignalDragonTigerDetail getDragonTigerDetail(String date, String code) {
        return dragonTigerDetailMapper.selectByDateAndStock(date, code);
    }

    @Override
    @Cacheable(key = "'dragonTigerDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getDragonTigerDates() {
        return dragonTigerDetailMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(key = "'northboundLatest:' + #days", unless = "#result == null || #result.isEmpty()")
    public List<SignalNorthbound> getNorthboundLatest(int days) {
        return northboundMapper.selectLatest(days);
    }

    @Override
    public SignalNorthbound getNorthboundByDate(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        return northboundMapper.selectByDate(targetDate);
    }

    @Override
    @Cacheable(key = "'northboundDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getNorthboundDates() {
        return northboundMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(key = "'lockupByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupByStock(String code) {
        return lockupDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'lockupUpcoming'", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getUpcomingLockup() {
        return lockupDetailMapper.selectUpcoming(30);
    }

    @Override
    @Cacheable(key = "'lockupHistory'", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupHistory() {
        return lockupDetailMapper.selectByTag("history", 30);
    }

    @Override
    @Cacheable(key = "'industryCompare:' + #date", unless = "#result == null")
    public Map<String, Object> getIndustryCompare(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDailyIndustry> list = industryMapper.selectByDate(targetDate);
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(key = "'industryDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getIndustryDates() {
        return industryMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(key = "'conceptBlocks:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalConceptBlock> getConceptBlocks(String code) {
        return conceptBlockMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'conceptBlocks:' + #code + ':' + #type", unless = "#result == null || #result.isEmpty()")
    public List<SignalConceptBlock> getConceptBlocksByType(String code, String type) {
        return conceptBlockMapper.selectByStockAndType(code, type);
    }

    @Override
    @Cacheable(key = "'fundFlow:' + #code + ':' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<SignalFundFlow> getFundFlow(String code, int limit) {
        return fundFlowMapper.selectByStock(code, limit);
    }

    @Override
    @Cacheable(key = "'fundFlowSince:' + #code + ':' + #since", unless = "#result == null || #result.isEmpty()")
    public List<SignalFundFlow> getFundFlowSince(String code, String since) {
        return fundFlowMapper.selectByStockSince(code, since);
    }

    @Override
    @Cacheable(key = "'dragonTigerDetailByDate:' + #date", unless = "#result == null")
    public Map<String, Object> getDragonTigerDetailByDate(String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDragonTigerDetail> list = dragonTigerDetailMapper.selectByDate(targetDate);
        return Map.of("date", targetDate, "records", list, "total", list.size());
    }

    @Override
    @Cacheable(key = "'dragonTigerDetailByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalDragonTigerDetail> getDragonTigerDetailByStock(String code) {
        return dragonTigerDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'dragonTigerDetailDates'", unless = "#result == null || #result.isEmpty()")
    public List<String> getDragonTigerDetailDates() {
        return dragonTigerDetailMapper.selectAvailableDates();
    }

    @Override
    @Cacheable(key = "'lockupDetailByStock:' + #code", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupDetailByStock(String code) {
        return lockupDetailMapper.selectByStock(code);
    }

    @Override
    @Cacheable(key = "'lockupDetailUpcoming:' + #limit", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getUpcomingLockups(int limit) {
        return lockupDetailMapper.selectUpcoming(limit);
    }

    @Override
    @Cacheable(key = "'lockupDetailByTag:' + #code + ':' + #tag", unless = "#result == null || #result.isEmpty()")
    public List<SignalLockupDetail> getLockupByTag(String code, String tag) {
        return lockupDetailMapper.selectByStockAndTag(code, tag);
    }

    /**
     * 清空信号数据缓存（每日盘后数据刷新时调用）
     */
    @CacheEvict(allEntries = true)
    public void clearCache() {
        log.info("信号数据缓存已清空");
    }
}
