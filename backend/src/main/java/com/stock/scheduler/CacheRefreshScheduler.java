package com.stock.scheduler;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.CacheManager;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 缓存定时清理 — 兜底机制
 * <p>
 * Python 数据采集器每30分钟运行一次盘后数据刷新，
 * 若采集器调用 /api/cache/evict 失败，此定时任务确保缓存最多 TTL+5min 后自动过期。
 * </p>
 */
@Component
public class CacheRefreshScheduler {

    private static final Logger log = LoggerFactory.getLogger(CacheRefreshScheduler.class);

    @Autowired
    private CacheManager cacheManager;

    /**
     * 每30分钟执行一次缓存全量清理
     * 配合 Redis TTL 使用：时薪类数据(TTL=5~30min)在清理后立即失效
     * 实时类数据(TTL=30s)不受影响
     */
    @Scheduled(fixedRate = 30 * 60 * 1000)
    public void refreshSignalCaches() {
        String[] caches = {"signalHotData", "signalDragonTiger",
                           "signalReferenceData", "signalMarketData",
                           "signalRealtime"};
        for (String name : caches) {
            try {
                var cache = cacheManager.getCache(name);
                if (cache != null) {
                    cache.clear();
                }
            } catch (Exception e) {
                log.warn("定时清理缓存 {} 失败: {}", name, e.getMessage());
            }
        }
        log.debug("缓存定时清理完成");
    }
}
