package com.stock.controller;

import com.stock.service.SignalDataService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 信号数据控制器 — 委托给 SignalDataService，含缓存
 */
@RestController
@RequestMapping("/api/signal")
public class SignalDataController {

    private final SignalDataService signalDataService;

    public SignalDataController(SignalDataService signalDataService) {
        this.signalDataService = signalDataService;
    }

    // ==================== 题材热点 ====================
    @GetMapping("/hot-reason")
    public ResponseEntity<?> getHotReason(@RequestParam(required = false) String date) {
        return ResponseEntity.ok(signalDataService.getHotReason(date));
    }

    @GetMapping("/hot-reason/dates")
    public ResponseEntity<List<String>> getHotReasonDates() {
        return ResponseEntity.ok(signalDataService.getHotReasonDates());
    }

    // ==================== 龙虎榜 ====================
    @GetMapping("/dragon-tiger/daily")
    public ResponseEntity<?> getDragonTigerDaily(@RequestParam(required = false) String date) {
        return ResponseEntity.ok(signalDataService.getDragonTigerDaily(date));
    }

    @GetMapping("/dragon-tiger/stock/{code}")
    public ResponseEntity<?> getDragonTigerByStock(@PathVariable String code) {
        return ResponseEntity.ok(signalDataService.getDragonTigerByStock(code));
    }

    @GetMapping("/dragon-tiger/detail")
    public ResponseEntity<?> getDragonTigerDetail(
            @RequestParam String date, @RequestParam String code) {
        var record = signalDataService.getDragonTigerDetail(date, code);
        if (record == null) return ResponseEntity.status(404).build();
        return ResponseEntity.ok(record);
    }

    @GetMapping("/dragon-tiger/dates")
    public ResponseEntity<List<String>> getDragonTigerDates() {
        return ResponseEntity.ok(signalDataService.getDragonTigerDates());
    }

    // ==================== 北向资金 ====================
    @GetMapping("/northbound/latest")
    public ResponseEntity<?> getNorthboundLatest(@RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(signalDataService.getNorthboundLatest(days));
    }

    @GetMapping("/northbound/date")
    public ResponseEntity<?> getNorthboundByDate(@RequestParam(required = false) String date) {
        var record = signalDataService.getNorthboundByDate(date);
        if (record == null) return ResponseEntity.status(404).build();
        return ResponseEntity.ok(record);
    }

    @GetMapping("/northbound/dates")
    public ResponseEntity<List<String>> getNorthboundDates() {
        return ResponseEntity.ok(signalDataService.getNorthboundDates());
    }

    // ==================== 限售解禁 ====================
    @GetMapping("/lockup/stock/{code}")
    public ResponseEntity<?> getLockupByStock(@PathVariable String code) {
        return ResponseEntity.ok(signalDataService.getLockupByStock(code));
    }

    @GetMapping("/lockup/upcoming")
    public ResponseEntity<?> getUpcomingLockup() {
        return ResponseEntity.ok(signalDataService.getUpcomingLockup());
    }

    @GetMapping("/lockup/history")
    public ResponseEntity<?> getLockupHistory() {
        return ResponseEntity.ok(signalDataService.getLockupHistory());
    }

    // ==================== 行业排行 ====================
    @GetMapping("/industry-compare")
    public ResponseEntity<?> getIndustryCompare(@RequestParam(required = false) String date) {
        return ResponseEntity.ok(signalDataService.getIndustryCompare(date));
    }

    @GetMapping("/industry-compare/dates")
    public ResponseEntity<List<String>> getIndustryDates() {
        return ResponseEntity.ok(signalDataService.getIndustryDates());
    }

    // ==================== 概念板块 ====================
    @GetMapping("/concept-blocks/{code}")
    public ResponseEntity<?> getConceptBlocks(@PathVariable String code) {
        return ResponseEntity.ok(signalDataService.getConceptBlocks(code));
    }

    @GetMapping("/concept-blocks/{code}/{type}")
    public ResponseEntity<?> getConceptBlocksByType(@PathVariable String code, @PathVariable String type) {
        return ResponseEntity.ok(signalDataService.getConceptBlocksByType(code, type));
    }

    // ==================== 资金流向 ====================
    @GetMapping("/fund-flow/{code}")
    public ResponseEntity<?> getFundFlow(@PathVariable String code, @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(signalDataService.getFundFlow(code, limit));
    }

    @GetMapping("/fund-flow/since")
    public ResponseEntity<?> getFundFlowSince(@RequestParam String code, @RequestParam String since) {
        return ResponseEntity.ok(signalDataService.getFundFlowSince(code, since));
    }

    // ==================== 龙虎榜明细 ====================
    @GetMapping("/dragon-tiger-detail")
    public ResponseEntity<?> getDragonTigerDetailByDate(@RequestParam(required = false) String date) {
        return ResponseEntity.ok(signalDataService.getDragonTigerDetailByDate(date));
    }

    @GetMapping("/dragon-tiger-detail/stock/{code}")
    public ResponseEntity<?> getDragonTigerDetailByStock(@PathVariable String code) {
        return ResponseEntity.ok(signalDataService.getDragonTigerDetailByStock(code));
    }

    @GetMapping("/dragon-tiger-detail/dates")
    public ResponseEntity<List<String>> getDragonTigerDetailDates() {
        return ResponseEntity.ok(signalDataService.getDragonTigerDetailDates());
    }

    // ==================== 解禁明细 ====================
    @GetMapping("/lockup-detail/{code}")
    public ResponseEntity<?> getLockupDetailByStock(@PathVariable String code) {
        return ResponseEntity.ok(signalDataService.getLockupDetailByStock(code));
    }

    @GetMapping("/lockup-detail/upcoming")
    public ResponseEntity<?> getUpcomingLockups(@RequestParam(defaultValue = "50") int limit) {
        return ResponseEntity.ok(signalDataService.getUpcomingLockups(limit));
    }

    @GetMapping("/lockup-detail/{code}/{tag}")
    public ResponseEntity<?> getLockupByTag(@PathVariable String code, @PathVariable String tag) {
        return ResponseEntity.ok(signalDataService.getLockupByTag(code, tag));
    }
}
