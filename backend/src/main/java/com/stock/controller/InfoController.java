package com.stock.controller;

import com.stock.entity.*;
import com.stock.service.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 资讯层统一控制器 — 研报 + 新闻 + 公告
 *
 * 从 a-stock-data 项目的研报层、新闻层、公告层迁移合并
 * 路由前缀: /api/info
 *
 * 数据关联说明:
 * - 研报与PDF: 通过 reportId 关联 info_report_pdf
 * - 个股新闻/研报/公告: 通过 stockCode 关联 stock 表
 * - 财联社快讯/全球资讯: 全局资讯，不依赖个股
 */
@RestController
@RequestMapping("/api/info")
public class InfoController {

    @Autowired
    private InfoResearchReportService researchReportService;

    @Autowired
    private InfoConsensusEpsService consensusEpsService;

    @Autowired
    private InfoStockNewsService stockNewsService;

    @Autowired
    private InfoClsNewsService clsNewsService;

    @Autowired
    private InfoGlobalNewsService globalNewsService;

    @Autowired
    private InfoFilingService filingService;

    @Autowired
    private InfoReportPdfService reportPdfService;

    // ============================================================
    // 研报层 — Research Reports
    // ============================================================

    @GetMapping("/research/{code}")
    public ResponseEntity<?> getResearchReports(@PathVariable String code) {
        List<InfoResearchReport> list = researchReportService.getByStock(code);
        if (list.isEmpty()) {
            return ResponseEntity.ok(Map.of("stockCode", code, "records", list,
                    "note", "暂无研报数据"));
        }
        return ResponseEntity.ok(Map.of("stockCode", code, "records", list, "total", list.size()));
    }

    @GetMapping("/research/range")
    public ResponseEntity<List<InfoResearchReport>> getResearchByDateRange(
            @RequestParam String code,
            @RequestParam String startDate,
            @RequestParam String endDate) {
        return ResponseEntity.ok(researchReportService.getByStockAndDateRange(code, startDate, endDate));
    }

    @GetMapping("/research/org")
    public ResponseEntity<List<InfoResearchReport>> getResearchByOrg(
            @RequestParam String org,
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(researchReportService.getByOrg(org, limit));
    }

    @GetMapping("/research/stocks")
    public ResponseEntity<List<String>> getResearchStocks() {
        return ResponseEntity.ok(researchReportService.getBaseMapper().selectAvailableStocks());
    }

    // ============================================================
    // 一致预期EPS — Consensus EPS
    // ============================================================

    @GetMapping("/consensus-eps/{code}")
    public ResponseEntity<List<InfoConsensusEps>> getConsensusEps(@PathVariable String code) {
        return ResponseEntity.ok(consensusEpsService.getByStock(code));
    }

    @GetMapping("/consensus-eps/{code}/{year}")
    public ResponseEntity<InfoConsensusEps> getConsensusEpsByYear(
            @PathVariable String code, @PathVariable String year) {
        InfoConsensusEps record = consensusEpsService.getByStockAndYear(code, year);
        if (record == null) {
            return ResponseEntity.status(404).build();
        }
        return ResponseEntity.ok(record);
    }

    // ============================================================
    // 个股新闻 — Stock News
    // ============================================================

    @GetMapping("/news/{code}")
    public ResponseEntity<?> getStockNews(
            @PathVariable String code,
            @RequestParam(defaultValue = "20") int limit) {
        List<InfoStockNews> list = stockNewsService.getByStock(code, limit);
        if (list.isEmpty()) {
            return ResponseEntity.ok(Map.of("stockCode", code, "records", list,
                    "note", "暂无个股新闻"));
        }
        return ResponseEntity.ok(Map.of("stockCode", code, "records", list, "total", list.size()));
    }

    @GetMapping("/news/since")
    public ResponseEntity<List<InfoStockNews>> getStockNewsSince(
            @RequestParam String code,
            @RequestParam String since) {
        return ResponseEntity.ok(stockNewsService.getByStockSince(code, since));
    }

    // ============================================================
    // 财联社快讯 — CLS News
    // ============================================================

    @GetMapping("/cls-news")
    public ResponseEntity<?> getClsNews(@RequestParam(defaultValue = "30") int limit) {
        List<InfoClsNews> list = clsNewsService.getLatest(limit);
        return ResponseEntity.ok(Map.of("records", list, "total", list.size()));
    }

    @GetMapping("/cls-news/since")
    public ResponseEntity<List<InfoClsNews>> getClsNewsSince(@RequestParam String since) {
        return ResponseEntity.ok(clsNewsService.getSince(since));
    }

    // ============================================================
    // 全球资讯 — Global News
    // ============================================================

    @GetMapping("/global-news")
    public ResponseEntity<?> getGlobalNews(@RequestParam(defaultValue = "20") int limit) {
        List<InfoGlobalNews> list = globalNewsService.getLatest(limit);
        return ResponseEntity.ok(Map.of("records", list, "total", list.size()));
    }

    // ============================================================
    // 巨潮公告 — Filings
    // ============================================================

    @GetMapping("/filing/{code}")
    public ResponseEntity<?> getFilings(
            @PathVariable String code,
            @RequestParam(defaultValue = "20") int limit) {
        List<InfoFiling> list = filingService.getByStock(code, limit);
        if (list.isEmpty()) {
            return ResponseEntity.ok(Map.of("stockCode", code, "records", list,
                    "note", "暂无公告数据"));
        }
        return ResponseEntity.ok(Map.of("stockCode", code, "records", list, "total", list.size()));
    }

    @GetMapping("/filing/range")
    public ResponseEntity<List<InfoFiling>> getFilingsByDateRange(
            @RequestParam String code,
            @RequestParam String startDate,
            @RequestParam String endDate) {
        return ResponseEntity.ok(filingService.getByStockAndDateRange(code, startDate, endDate));
    }

    @GetMapping("/filing/type")
    public ResponseEntity<List<InfoFiling>> getFilingsByType(
            @RequestParam String type,
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(filingService.getByType(type, limit));
    }

    // ============================================================
    // 研报PDF — Report PDF
    // ============================================================

    @GetMapping("/pdf/stock/{code}")
    public ResponseEntity<List<InfoReportPdf>> getPdfsByStock(@PathVariable String code) {
        return ResponseEntity.ok(reportPdfService.getByStock(code));
    }

    @GetMapping("/pdf/report/{reportId}")
    public ResponseEntity<InfoReportPdf> getPdfByReport(@PathVariable Long reportId) {
        InfoReportPdf pdf = reportPdfService.getByReportId(reportId);
        if (pdf == null) {
            return ResponseEntity.status(404).build();
        }
        return ResponseEntity.ok(pdf);
    }

    // ============================================================
    // 全层聚合查询 — Aggregate query across all info layers
    // ============================================================

    @GetMapping("/all/{code}")
    public ResponseEntity<Map<String, Object>> getAllInfo(@PathVariable String code) {
        Map<String, Object> result = new java.util.LinkedHashMap<>();
        result.put("stockCode", code);

        // 研报
        List<InfoResearchReport> reports = researchReportService.getByStock(code);
        result.put("researchReports", Map.of("total", reports.size(), "records", reports.stream().limit(5).toList()));

        // 一致预期
        List<InfoConsensusEps> eps = consensusEpsService.getByStock(code);
        result.put("consensusEps", eps);

        // 个股新闻
        List<InfoStockNews> news = stockNewsService.getByStock(code, 10);
        result.put("stockNews", Map.of("total", news.size(), "records", news));

        // 公告
        List<InfoFiling> filings = filingService.getByStock(code, 10);
        result.put("filings", Map.of("total", filings.size(), "records", filings));

        // PDF
        List<InfoReportPdf> pdfs = reportPdfService.getByStock(code);
        result.put("reportPdfs", Map.of("total", pdfs.size(), "records", pdfs));

        return ResponseEntity.ok(result);
    }
}
