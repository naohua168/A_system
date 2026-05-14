package com.stock.controller;

import com.stock.entity.*;
import com.stock.mapper.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/signal")
public class SignalDataController {

    @Autowired
    private SignalHotReasonMapper hotReasonMapper;
    @Autowired
    private SignalDragonTigerMapper dragonTigerMapper;
    @Autowired
    private SignalNorthboundMapper northboundMapper;
    @Autowired
    private SignalLockupMapper lockupMapper;
    @Autowired
    private SignalDailyIndustryMapper industryMapper;

    // ==================== 题材热点 ====================
    @GetMapping("/hot-reason")
    public ResponseEntity<?> getHotReason(@RequestParam(required = false) String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalHotReason> list = hotReasonMapper.selectByDate(targetDate);
        if (list.isEmpty()) {
            return ResponseEntity.ok(Map.of("date", targetDate, "records", list,
                "note", "当日无强势股数据，盘后15:30后更新"));
        }
        return ResponseEntity.ok(Map.of("date", targetDate, "records", list, "total", list.size()));
    }

    @GetMapping("/hot-reason/dates")
    public ResponseEntity<List<String>> getHotReasonDates() {
        return ResponseEntity.ok(hotReasonMapper.selectAvailableDates());
    }

    // ==================== 龙虎榜 ====================
    @GetMapping("/dragon-tiger/daily")
    public ResponseEntity<?> getDragonTigerDaily(@RequestParam(required = false) String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDragonTiger> list = dragonTigerMapper.selectDailyByDate(targetDate);
        return ResponseEntity.ok(Map.of("date", targetDate, "records", list, "total", list.size()));
    }

    @GetMapping("/dragon-tiger/stock/{code}")
    public ResponseEntity<List<SignalDragonTiger>> getDragonTigerByStock(@PathVariable String code) {
        return ResponseEntity.ok(dragonTigerMapper.selectByStock(code));
    }

    @GetMapping("/dragon-tiger/detail")
    public ResponseEntity<SignalDragonTiger> getDragonTigerDetail(
            @RequestParam String date, @RequestParam String code) {
        SignalDragonTiger record = dragonTigerMapper.selectByDateAndStock(date, code);
        if (record == null) return ResponseEntity.status(404).build();
        return ResponseEntity.ok(record);
    }

    @GetMapping("/dragon-tiger/dates")
    public ResponseEntity<List<String>> getDragonTigerDates() {
        return ResponseEntity.ok(dragonTigerMapper.selectAvailableDates());
    }

    // ==================== 北向资金 ====================
    @GetMapping("/northbound/latest")
    public ResponseEntity<List<SignalNorthbound>> getNorthboundLatest(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(northboundMapper.selectLatest(days));
    }

    @GetMapping("/northbound/date")
    public ResponseEntity<SignalNorthbound> getNorthboundByDate(
            @RequestParam(required = false) String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        SignalNorthbound record = northboundMapper.selectByDate(targetDate);
        if (record == null) return ResponseEntity.status(404).build();
        return ResponseEntity.ok(record);
    }

    @GetMapping("/northbound/dates")
    public ResponseEntity<List<String>> getNorthboundDates() {
        return ResponseEntity.ok(northboundMapper.selectAvailableDates());
    }

    // ==================== 限售解禁 ====================
    @GetMapping("/lockup/stock/{code}")
    public ResponseEntity<List<SignalLockup>> getLockupByStock(@PathVariable String code) {
        return ResponseEntity.ok(lockupMapper.selectByStock(code));
    }

    @GetMapping("/lockup/upcoming")
    public ResponseEntity<List<SignalLockup>> getUpcomingLockup() {
        return ResponseEntity.ok(lockupMapper.selectUpcoming());
    }

    @GetMapping("/lockup/history")
    public ResponseEntity<List<SignalLockup>> getLockupHistory() {
        return ResponseEntity.ok(lockupMapper.selectHistory());
    }

    // ==================== 行业排行 ====================
    @GetMapping("/industry-compare")
    public ResponseEntity<?> getIndustryCompare(@RequestParam(required = false) String date) {
        String targetDate = (date != null) ? date : LocalDate.now().toString();
        List<SignalDailyIndustry> list = industryMapper.selectByDate(targetDate);
        return ResponseEntity.ok(Map.of("date", targetDate, "records", list, "total", list.size()));
    }

    @GetMapping("/industry-compare/dates")
    public ResponseEntity<List<String>> getIndustryDates() {
        return ResponseEntity.ok(industryMapper.selectAvailableDates());
    }
}
