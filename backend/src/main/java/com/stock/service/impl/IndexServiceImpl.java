package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.stock.entity.MarketIndex;
import com.stock.entity.IndexDaily;
import com.stock.mapper.IndexDailyMapper;
import com.stock.mapper.MarketIndexMapper;
import com.stock.service.IndexService;
import org.springframework.stereotype.Service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
public class IndexServiceImpl implements IndexService {

    private static final Logger log = LoggerFactory.getLogger(IndexServiceImpl.class);

    private final MarketIndexMapper marketIndexMapper;
    private final IndexDailyMapper indexDailyMapper;

    public IndexServiceImpl(MarketIndexMapper marketIndexMapper, IndexDailyMapper indexDailyMapper) {
        this.marketIndexMapper = marketIndexMapper;
        this.indexDailyMapper = indexDailyMapper;
    }

    @Override
    public List<Map<String, Object>> getIndexList() {
        // 先试试关联查询带最新行情（失败时静默回退到手动关联）
        try {
            List<Map<String, Object>> ranking = indexDailyMapper.selectIndexRanking();
            if (ranking != null && !ranking.isEmpty()) return ranking;
        } catch (Exception e) {
            log.warn("索引关联查询失败，回退到手动关联: {}", e.getMessage());
        }

        // 回退：手动关联
        List<MarketIndex> indices = marketIndexMapper.selectList(null);
        String maxDate = indexDailyMapper.selectMaxTradeDate();
        if (maxDate == null) {
            // 新数据可能还不在DB中，尝试用today
            maxDate = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
        }

        List<Map<String, Object>> result = new ArrayList<>();
        for (MarketIndex idx : indices) {
            Map<String, Object> map = new HashMap<>();
            map.put("indexCode", idx.getIndexCode());
            map.put("indexName", idx.getIndexName());
            map.put("market", idx.getMarket());
            map.put("category", idx.getCategory());

            // 查最新行情
            List<IndexDaily> latest = indexDailyMapper.selectRecent(idx.getIndexCode(), 1);
            if (!latest.isEmpty()) {
                IndexDaily d = latest.get(0);
                map.put("closePoint", d.getClosePoint());
                map.put("changePercent", d.getChangePercent());
                map.put("tradeDate", d.getTradeDate() != null ? d.getTradeDate().toString() : null);
            }
            result.add(map);
        }
        return result;
    }

    @Override
    public MarketIndex getIndexInfo(String indexCode) {
        LambdaQueryWrapper<MarketIndex> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MarketIndex::getIndexCode, indexCode);
        return marketIndexMapper.selectOne(wrapper);
    }

    @Override
    public List<IndexDaily> getKlineData(String indexCode, int days) {
        return indexDailyMapper.selectRecent(indexCode, days);
    }

    @Override
    public String getMaxTradeDate() {
        return indexDailyMapper.selectMaxTradeDate();
    }
}
