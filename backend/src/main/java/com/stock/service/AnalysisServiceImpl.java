package com.stock.service.impl;

import com.stock.service.AnalysisService;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class AnalysisServiceImpl implements AnalysisService {

    // Python 运行路径（按实际情况调整）
    private static final String PYTHON = "python";
    private static final String BRIDGE_SCRIPT = "../analysis-algorithms/chanlun_bridge.py";

    @Override
    public Map<String, Object> getChanlunAnalysis(String stockCode, int days) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    PYTHON, "-W", "ignore", BRIDGE_SCRIPT,
                    "--code", stockCode,
                    "--days", String.valueOf(days)
            );
            pb.directory(new java.io.File(".").getAbsoluteFile().getParentFile());

            Process process = pb.start();
            String jsonOutput;
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), java.nio.charset.StandardCharsets.UTF_8))) {
                jsonOutput = reader.lines().collect(Collectors.joining("\n"));
            }

            int exitCode = process.waitFor();
            if (exitCode != 0) {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "Python进程退出码: " + exitCode);
                return error;
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> result = new com.fasterxml.jackson.databind.ObjectMapper()
                    .readValue(jsonOutput, Map.class);
            return result;

        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("error", "缠论分析失败: " + e.getMessage());
            return error;
        }
    }

    // ==================== 以下为已有方法的空实现 ====================

    @Override
    public boolean save(com.stock.entity.AnalysisResult result) {
        return false;
    }

    @Override
    public List<Map<String, Object>> getYearlyReturn(String stockCode, int years) {
        return Collections.emptyList();
    }

    @Override
    public List<Map<String, Object>> getMonthlyReturn(String stockCode, int months) {
        return Collections.emptyList();
    }

    @Override
    public Map<String, Object> getTrendAnalysis(String stockCode, int days) {
        return Collections.emptyMap();
    }

    @Override
    public List<Map<String, Object>> filterStocks(Map<String, Object> conditions) {
        return Collections.emptyList();
    }

    @Override
    public BigDecimal getCorrelation(String codeA, String codeB, int days) {
        return BigDecimal.ZERO;
    }

    @Override
    public List<Map<String, Object>> getSectorRanking(String tradeDate) {
        return Collections.emptyList();
    }
}
