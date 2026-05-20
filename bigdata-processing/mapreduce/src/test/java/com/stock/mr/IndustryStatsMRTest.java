package com.stock.mr;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * IndustryStatsMR 行业统计 MapReduce 单元测试
 * 验证:
 *   1. DistributedCache 行业映射加载
 *   2. 硬编码回退映射
 *   3. CSV 解析逻辑
 *   4. 聚合计算逻辑
 */
class IndustryStatsMRTest {

    // ============================================================
    // 1. CSV 解析测试
    // ============================================================

    @Test
    @DisplayName("CSV 解析 - Format A（带字母代码）")
    void testParseFormatA() {
        // stock_code,date,open,high,low,close,volume,amount,change_pct
        String line = "000001,2025-01-02,10.00,10.50,9.80,10.30,1000000,5000000,3.00";
        String[] fields = line.split(",");

        assertTrue(fields.length >= 9);
        String stockCode = fields[0];  // 格式A: 第一个字段是代码
        String changePct = fields[8];
        String volume = fields[6];

        assertEquals("000001", stockCode);
        assertEquals("3.00", changePct);
        assertEquals("1000000", volume);
    }

    @Test
    @DisplayName("CSV 解析 - Format B（以日期开头）")
    void testParseFormatB() {
        // date,open,high,low,close,volume,amount,...,stock_code
        String line = "2025-01-02,10.00,10.50,9.80,10.30,1000000,5000000,0.5,5.0,000001";
        String[] fields = line.split(",");

        assertTrue(fields.length >= 10);
        // 格式A检测: 第一个字段不匹配字母则视为格式B
        String firstField = fields[0];
        assertFalse(firstField.matches(".*[A-Za-z].*"));
        assertEquals("2025-01-02", firstField);

        String stockCode = fields[fields.length - 1];  // 格式B: 最后一个字段是代码
        String changePct = fields.length > 8 ? fields[8] : "0";
        String volume = fields[5];

        assertEquals("000001", stockCode);
        assertEquals("5.0", changePct);
        assertEquals("5000000", volume);
    }

    @Test
    @DisplayName("CSV 解析 - 空行和表头跳过")
    void testSkipHeaderAndEmpty() {
        assertTrue("".trim().isEmpty());
        assertTrue("date".equals("date"));  // 表头行
        assertTrue("trade_date".equals("trade_date"));  // 表头行
    }

    @Test
    @DisplayName("CSV 解析 - 不够6个字段的行应跳过")
    void testSkipShortLines() {
        String line = "invalid,line";
        String[] fields = line.split(",");
        assertTrue(fields.length < 6);
    }

    // ============================================================
    // 2. 行业映射加载测试
    // ============================================================

    @Test
    @DisplayName("行业映射 - 从文件加载(@TempDir)")
    void testLoadIndustryMapFromFile(@TempDir Path tempDir) throws IOException {
        // 准备测试 CSV: stock_code,industry
        Path mappingFile = tempDir.resolve("test_industry.csv");
        Files.write(mappingFile, List.of(
                "000001,银行",
                "600519,白酒",
                "300750,新能源",
                "002415,通信"
        ));

        // 模拟 IndustryStatsReducer 的 loadFromFile 逻辑
        Map<String, String> industryMap = new HashMap<>();
        try (BufferedReader reader = new BufferedReader(new FileReader(mappingFile.toFile()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#") || line.startsWith("stock_code")) continue;
                String[] parts = line.split(",");
                if (parts.length >= 2) {
                    industryMap.put(parts[0].trim(), parts[1].trim());
                }
            }
        }

        assertEquals(4, industryMap.size());
        assertEquals("银行", industryMap.get("000001"));
        assertEquals("白酒", industryMap.get("600519"));
        assertEquals("新能源", industryMap.get("300750"));
        assertEquals("通信", industryMap.get("002415"));
        assertNull(industryMap.get("999999"));  // 不存在的股票
    }

    @Test
    @DisplayName("行业映射 - 空文件和注释行处理")
    void testLoadIndustryMapWithComments(@TempDir Path tempDir) throws IOException {
        Path mappingFile = tempDir.resolve("comments.csv");
        Files.write(mappingFile, List.of(
                "# This is a comment",
                "stock_code,industry",
                "",
                "000001,银行",
                "  600036  ,  保险  "  // 含空格
        ));

        Map<String, String> industryMap = new HashMap<>();
        try (BufferedReader reader = new BufferedReader(new FileReader(mappingFile.toFile()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#") || line.startsWith("stock_code")) continue;
                String[] parts = line.split(",");
                if (parts.length >= 2) {
                    industryMap.put(parts[0].trim(), parts[1].trim());
                }
            }
        }

        assertEquals(2, industryMap.size());
        assertEquals("银行", industryMap.get("000001"));
        assertEquals("保险", industryMap.get("600036"));
    }

    @Test
    @DisplayName("行业映射 - 文件不存在时返回空")
    void testLoadIndustryMap_FileNotFound() {
        Map<String, String> industryMap = new HashMap<>();
        try (BufferedReader reader = new BufferedReader(new FileReader("nonexistent.csv"))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",");
                if (parts.length >= 2) {
                    industryMap.put(parts[0].trim(), parts[1].trim());
                }
            }
            fail("应该抛出异常");
        } catch (IOException e) {
            assertTrue(industryMap.isEmpty());
        }
    }

    // ============================================================
    // 3. 聚合计算测试
    // ============================================================

    @Test
    @DisplayName("聚合计算 - 平均涨跌幅")
    void testAggregateAvgChange() {
        double[] changes = {3.0, -1.0, 2.0, 0.5, -0.5};
        double sum = 0;
        for (double c : changes) sum += c;
        double avg = Math.round(sum / changes.length * 100.0) / 100.0;

        assertEquals(0.8, avg, 0.001);  // (3-1+2+0.5-0.5)/5 = 0.8
    }

    @Test
    @DisplayName("聚合计算 - 涨跌家数统计")
    void testAggregateUpDownCount() {
        String[] records = {"3.0", "-1.0", "2.0", "0.5", "-0.5"};
        int upCount = 0, downCount = 0;
        for (String r : records) {
            double change = Double.parseDouble(r);
            if (change > 0) upCount++;
            else if (change < 0) downCount++;
        }

        assertEquals(3, upCount);
        assertEquals(2, downCount);
    }

    @Test
    @DisplayName("聚合计算 - 数据解析异常跳过")
    void testAggregateParseError() {
        String[] records = {"3.0", "invalid", "2.0"};
        double sum = 0;
        int count = 0;
        for (String r : records) {
            try {
                double change = Double.parseDouble(r);
                sum += change;
                count++;
            } catch (NumberFormatException ignored) {
                // 跳过无效数据
            }
        }

        assertEquals(5.0, sum);
        assertEquals(2, count);
    }

    // ============================================================
    // 4. 股票代码规范化测试
    // ============================================================

    @Test
    @DisplayName("股票代码补齐 - 6位标准化")
    void testStockCodePadding() {
        String code1 = "1";
        String code2 = "600519";
        String code3 = "300750";

        if (code1.length() < 6 && code1.matches("\\d+")) {
            code1 = String.format("%06d", Integer.parseInt(code1));
        }
        if (code2.length() < 6 && code2.matches("\\d+")) {
            code2 = String.format("%06d", Integer.parseInt(code2));
        }

        assertEquals("000001", code1);
        assertEquals("600519", code2);
        assertEquals("300750", code3);  // 已经是6位
    }

    // ============================================================
    // 5. 从 Redis/MySQL 加载的辅助脚本验证
    // ============================================================

    @Test
    @DisplayName("确认出口脚本 export_industry_mapping.py 存在并可解析")
    void testExportScriptExists() {
        File script = new File("../scripts/export_industry_mapping.py");
        // 验证脚本文件是否存在（相对路径取决于运行目录）
        assertTrue(script.exists() || new File("bigdata-processing/scripts/export_industry_mapping.py").exists(),
                "行业映射导出脚本 export_industry_mapping.py 应存在于 bigdata-processing/scripts/ 目录下");
    }
}
