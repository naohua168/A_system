package com.stock.controller;

import com.stock.service.SignalDataService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Collections;

@RestController
@RequestMapping("/api/signal")
public class SignalDataController {

    private static final Logger log = LoggerFactory.getLogger(SignalDataController.class);
    private final SignalDataService signalDataService;

    public SignalDataController(SignalDataService signalDataService) {
        this.signalDataService = signalDataService;
    }

    private ResponseEntity<?> okOrEmpty(Object result) {
        return ResponseEntity.ok(result != null ? result : Collections.emptyList());
    }

    @GetMapping("/hot-reason")
    public ResponseEntity<?> getHotReason(@RequestParam(required = false) String date) {
        try { return okOrEmpty(signalDataService.getHotReason(date));
        } catch (Exception e) { log.warn("hot-reason: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/hot-reason/dates")
    public ResponseEntity<?> getHotReasonDates() {
        try { return okOrEmpty(signalDataService.getHotReasonDates());
        } catch (Exception e) { log.warn("hot-reason/dates: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/dragon-tiger/daily")
    public ResponseEntity<?> getDragonTigerDaily(@RequestParam(required = false) String date) {
        try { return okOrEmpty(signalDataService.getDragonTigerDaily(date));
        } catch (Exception e) { log.warn("dragon-tiger/daily: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/dragon-tiger/stock/{code}")
    public ResponseEntity<?> getDragonTigerByStock(@PathVariable String code) {
        try { return okOrEmpty(signalDataService.getDragonTigerByStock(code));
        } catch (Exception e) { log.warn("dragon-tiger/stock: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/dragon-tiger/detail")
    public ResponseEntity<?> getDragonTigerDetail(@RequestParam String date, @RequestParam String code) {
        try {
            var record = signalDataService.getDragonTigerDetail(date, code);
            if (record == null) return ResponseEntity.status(404).build();
            return ResponseEntity.ok(record);
        } catch (Exception e) { log.warn("dragon-tiger/detail: {}", e.getMessage()); return ResponseEntity.status(404).build(); }
    }

    @GetMapping("/dragon-tiger/dates")
    public ResponseEntity<?> getDragonTigerDates() {
        try { return okOrEmpty(signalDataService.getDragonTigerDates());
        } catch (Exception e) { log.warn("dragon-tiger/dates: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/northbound/latest")
    public ResponseEntity<?> getNorthboundLatest(@RequestParam(defaultValue = "30") int days) {
        try { return okOrEmpty(signalDataService.getNorthboundLatest(days));
        } catch (Exception e) { log.warn("northbound/latest: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/northbound/date")
    public ResponseEntity<?> getNorthboundByDate(@RequestParam(required = false) String date) {
        try {
            var record = signalDataService.getNorthboundByDate(date);
            if (record == null) return ResponseEntity.status(404).build();
            return ResponseEntity.ok(record);
        } catch (Exception e) { log.warn("northbound/date: {}", e.getMessage()); return ResponseEntity.status(404).build(); }
    }

    @GetMapping("/northbound/dates")
    public ResponseEntity<?> getNorthboundDates() {
        try { return okOrEmpty(signalDataService.getNorthboundDates());
        } catch (Exception e) { log.warn("northbound/dates: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/lockup/stock/{code}")
    public ResponseEntity<?> getLockupByStock(@PathVariable String code) {
        try { return okOrEmpty(signalDataService.getLockupByStock(code));
        } catch (Exception e) { log.warn("lockup/stock: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/lockup/upcoming")
    public ResponseEntity<?> getUpcomingLockup() {
        try { return okOrEmpty(signalDataService.getUpcomingLockup());
        } catch (Exception e) { log.warn("lockup/upcoming: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/lockup/history")
    public ResponseEntity<?> getLockupHistory() {
        try { return okOrEmpty(signalDataService.getLockupHistory());
        } catch (Exception e) { log.warn("lockup/history: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/industry-compare")
    public ResponseEntity<?> getIndustryCompare(@RequestParam(required = false) String date) {
        try { return okOrEmpty(signalDataService.getIndustryCompare(date));
        } catch (Exception e) { log.warn("industry-compare: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/industry-compare/dates")
    public ResponseEntity<?> getIndustryDates() {
        try { return okOrEmpty(signalDataService.getIndustryDates());
        } catch (Exception e) { log.warn("industry-compare/dates: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/concept-blocks/{code}")
    public ResponseEntity<?> getConceptBlocks(@PathVariable String code) {
        try { return okOrEmpty(signalDataService.getConceptBlocks(code));
        } catch (Exception e) { log.warn("concept-blocks: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/concept-blocks/{code}/{type}")
    public ResponseEntity<?> getConceptBlocksByType(@PathVariable String code, @PathVariable String type) {
        try { return okOrEmpty(signalDataService.getConceptBlocksByType(code, type));
        } catch (Exception e) { log.warn("concept-blocks/type: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/fund-flow/{code}")
    public ResponseEntity<?> getFundFlow(@PathVariable String code, @RequestParam(defaultValue = "20") int limit) {
        try { return okOrEmpty(signalDataService.getFundFlow(code, limit));
        } catch (Exception e) { log.warn("fund-flow: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/fund-flow/since")
    public ResponseEntity<?> getFundFlowSince(@RequestParam String code, @RequestParam String since) {
        try { return okOrEmpty(signalDataService.getFundFlowSince(code, since));
        } catch (Exception e) { log.warn("fund-flow/since: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/dragon-tiger-detail")
    public ResponseEntity<?> getDragonTigerDetailByDate(@RequestParam(required = false) String date) {
        try { return okOrEmpty(signalDataService.getDragonTigerDetailByDate(date));
        } catch (Exception e) { log.warn("dragon-tiger-detail: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/dragon-tiger-detail/stock/{code}")
    public ResponseEntity<?> getDragonTigerDetailByStock(@PathVariable String code) {
        try { return okOrEmpty(signalDataService.getDragonTigerDetailByStock(code));
        } catch (Exception e) { log.warn("dragon-tiger-detail/stock: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/dragon-tiger-detail/dates")
    public ResponseEntity<?> getDragonTigerDetailDates() {
        try { return okOrEmpty(signalDataService.getDragonTigerDetailDates());
        } catch (Exception e) { log.warn("dragon-tiger-detail/dates: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/lockup-detail/{code}")
    public ResponseEntity<?> getLockupDetailByStock(@PathVariable String code) {
        try { return okOrEmpty(signalDataService.getLockupDetailByStock(code));
        } catch (Exception e) { log.warn("lockup-detail: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/lockup-detail/upcoming")
    public ResponseEntity<?> getUpcomingLockups(@RequestParam(defaultValue = "50") int limit) {
        try { return okOrEmpty(signalDataService.getUpcomingLockups(limit));
        } catch (Exception e) { log.warn("lockup-detail/upcoming: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }

    @GetMapping("/lockup-detail/{code}/{tag}")
    public ResponseEntity<?> getLockupByTag(@PathVariable String code, @PathVariable String tag) {
        try { return okOrEmpty(signalDataService.getLockupByTag(code, tag));
        } catch (Exception e) { log.warn("lockup-detail/tag: {}", e.getMessage()); return okOrEmpty(Collections.emptyList()); }
    }
}
