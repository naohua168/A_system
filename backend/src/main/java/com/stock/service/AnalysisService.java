package com.stock.service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 分析服务接口
 * 提供收益率计算、趋势分析、股票筛选等功能
 */
public interface AnalysisService {
    /** 保存分析结果 */
    boolean save(com.stock.entity.AnalysisResult result);

    /** 查询分析结果列表 */
    java.util.List<com.stock.entity.AnalysisResult> list(
            com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<com.stock.entity.AnalysisResult> wrapper);

    /** 按 ID 删除分析结果 */
    boolean removeById(Long id);

    /**
     * 获取股票年收益率
     * @param stockCode 股票代码
     * @param years 最近N年
     * @return 年收益率列表 [{year, yearlyReturn}]
     */
    List<Map<String, Object>> getYearlyReturn(String stockCode, int years);

    /**
     * 获取股票月收益率
     * @param stockCode 股票代码
     * @param months 最近N个月
     * @return 月收益率列表 [{yearMonth, monthlyReturn}]
     */
    List<Map<String, Object>> getMonthlyReturn(String stockCode, int months);

    /**
     * 获取趋势分析
     * @param stockCode 股票代码
     * @param days 最近N个交易日
     * @return 趋势数据 (MA5, MA10, MA20, MACD等)
     */
    Map<String, Object> getTrendAnalysis(String stockCode, int days);

    /**
     * 筛选股票（基于条件）
     * @param conditions 筛选条件
     * @return 符合条件的股票列表
     */
    List<Map<String, Object>> filterStocks(Map<String, Object> conditions);

    /**
     * 计算两只股票的相关性
     * @param codeA 股票A
     * @param codeB 股票B
     * @param days 计算天数
     * @return 相关系数
     */
    BigDecimal getCorrelation(String codeA, String codeB, int days);

    /**
     * 获取行业涨跌排行
     * @param tradeDate 交易日
     * @return 行业排行列表
     */
    List<Map<String, Object>> getSectorRanking(String tradeDate);

    /**
     * 获取缠论分析数据（供前端K线图渲染）
     * @param stockCode 股票代码
     * @param days K线天数
     * @return {bi, zhongshu, fengxing, buy_sell_points, stats}
     */
    Map<String, Object> getChanlunAnalysis(String stockCode, int days);
}
