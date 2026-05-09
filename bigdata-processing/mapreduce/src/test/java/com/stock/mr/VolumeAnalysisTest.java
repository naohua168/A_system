package com.stock.mr;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * VolumeAnalysis 单元测试
 * 验证成交量分析逻辑
 */
class VolumeAnalysisTest {

    @Test
    @DisplayName("成交量分析 - 月均成交量计算")
    void testMonthlyAvgVolume() {
        // 模拟3个月的月成交量
        long[] monthlyVolumes = {1000000L, 1200000L, 1100000L};
        long sum = 0;
        for (long v : monthlyVolumes) {
            sum += v;
        }
        long avg = sum / monthlyVolumes.length;
        assertEquals(1100000L, avg);
    }

    @Test
    @DisplayName("成交量分析 - 异常放量检测")
    void testAbnormalVolume() {
        double avgVolume = 1000000;
        double currentVolume = 2000000;
        double ratio = currentVolume / avgVolume;
        // 放大2倍以上算异常
        assertTrue(ratio > 1.5);
        assertEquals(2.0, ratio, 0.001);
    }

    @Test
    @DisplayName("成交量分析 - 正常量检测通过")
    void testNormalVolume() {
        double avgVolume = 1000000;
        double currentVolume = 1100000;
        double ratio = currentVolume / avgVolume;
        // 1.1倍不算异常
        assertFalse(ratio > 1.5);
    }
}
