package com.stock.controller;

import com.stock.dto.ApiResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.CacheManager;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 缓存管理控制器 — 供数据采集器盘后调用，通知后端缓存已过期
 * <p>
 * Python 数据采集器直写 MySQL，不经过 Spring Service，@CacheEvict 不会自动触发。
 * 采集完毕后需调用此接口手动清理缓存，避免前端展示旧数据。
 * </p>
 * 路由前缀: /api/cache
 */
@RestController
@RequestMapping("/api/cache")
public class CacheController {

    private static final Logger log = LoggerFactory.getLogger(CacheController.class);

    @Autowired
    private CacheManager cacheManager;

    /** 所有已知缓存名称 */
    private static final List<String> ALL_CACHE_NAMES = List.of(
            "realtime",           // 30s 实时行情
            "signalMarketData",   // 30s 市场信号
            "signalHotData",      // 5min 热点
            "signalDragonTiger",  // 5min 龙虎榜
            "signalReferenceData",// 15min 参考数据
            "stockList",          // 15min 股票列表
            "stockDaily",         // 15min K线
            "infoReport",         // 30min 研报
            "infoNews",           // 30min 新闻
            "infoFiling",         // 30min 公告
            "fundNav"             // 60min 基金净值
    );

    /**
     * 清理指定缓存（或全部缓存）
     *
     * @param name 缓存名称，不传则清理全部
     */
    @PostMapping("/evict")
    public ApiResponse evict(@RequestParam(required = false) String name) {
        List<String> evicted = new ArrayList<>();

        if (name != null && !name.isEmpty()) {
            clearCache(name);
            evicted.add(name);
        } else {
            for (String cn : ALL_CACHE_NAMES) {
                clearCache(cn);
                evicted.add(cn);
            }
        }

        log.info("缓存已清理: {}", evicted);
        return ApiResponse.ok(Map.of("evicted", evicted, "count", evicted.size()));
    }

    private void clearCache(String cacheName) {
        try {
            var cache = cacheManager.getCache(cacheName);
            if (cache != null) {
                cache.clear();
            }
        } catch (Exception e) {
            log.warn("清理缓存 {} 失败: {}", cacheName, e.getMessage());
        }
    }
}
