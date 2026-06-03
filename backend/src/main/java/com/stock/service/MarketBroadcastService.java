package com.stock.service;

import com.stock.websocket.MarketWebSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import java.util.Map;

@Service
@EnableScheduling
public class MarketBroadcastService {

    private static final Logger log = LoggerFactory.getLogger(MarketBroadcastService.class);

    @Autowired
    private RedisReader redisReader;

    /** 指数列表 — 15s，首页/指数详情使用 */
    @Scheduled(fixedRate = 15_000)
    public void broadcastIndices() {
        if (!MarketWebSocketHandler.hasSubscribers("indices")) return;
        try {
            Object data = redisReader.getAsList("market:index_list");
            MarketWebSocketHandler.broadcast("indices", data);
        } catch (Exception e) {
            log.warn("broadcastIndices 失败: {}", e.getMessage());
        }
    }

    /** 信号数据（北向+题材+行业+龙虎榜）— 15s，首页信号卡片使用 */
    @Scheduled(fixedRate = 15_000)
    public void broadcastSignals() {
        if (!MarketWebSocketHandler.hasSubscribers("signals")) return;
        try {
            var northbound = redisReader.getAsList("market:northbound");
            var hotReason = redisReader.getAsList("market:hot_reason");
            var industryCompare = redisReader.getAsList("market:industry_compare");
            var dragonTiger = redisReader.getAsJson("market:dragon_tiger");
            MarketWebSocketHandler.broadcast("signals", Map.of(
                "northbound", northbound,
                "hotReason", hotReason,
                "industryCompare", industryCompare,
                "dragonTiger", dragonTiger
            ));
        } catch (Exception e) {
            log.warn("broadcastSignals 失败: {}", e.getMessage());
        }
    }

    /** 市场统计 — 60s */
    @Scheduled(fixedRate = 60_000)
    public void broadcastStats() {
        if (!MarketWebSocketHandler.hasSubscribers("stats")) return;
        try {
            var sb = redisReader.getAsList("market:stock_basic");
            int up = 0, down = 0, flat = 0;
            for (var s : sb) {
                double pct = 0;
                Object cp = s.get("changePct");
                if (cp instanceof Number) pct = ((Number) cp).doubleValue();
                else if (cp instanceof String) pct = Double.parseDouble((String) cp);
                if (pct > 0) up++;
                else if (pct < 0) down++;
                else flat++;
            }
            MarketWebSocketHandler.broadcast("stats", Map.of(
                "total", sb.size(), "up", up, "down", down, "flat", flat
            ));
        } catch (Exception e) {
            log.warn("broadcastStats 失败: {}", e.getMessage());
        }
    }

    /** 行业云图 — 120s */
    @Scheduled(fixedRate = 120_000)
    public void broadcastSector() {
        if (!MarketWebSocketHandler.hasSubscribers("sector")) return;
        try {
            Object data = redisReader.getAsList("market:industry_treemap");
            MarketWebSocketHandler.broadcast("sector", data);
        } catch (Exception e) {
            log.warn("broadcastSector 失败: {}", e.getMessage());
        }
    }
}
