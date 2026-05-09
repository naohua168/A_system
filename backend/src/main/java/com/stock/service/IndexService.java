package com.stock.service;

import com.stock.entity.MarketIndex;
import com.stock.entity.IndexDaily;
import java.util.List;
import java.util.Map;

public interface IndexService {

    /** 获取所有指数列表（带最新行情） */
    List<Map<String, Object>> getIndexList();

    /** 获取指数基本信息 */
    MarketIndex getIndexInfo(String indexCode);

    /** 获取指数K线数据 */
    List<IndexDaily> getKlineData(String indexCode, int days);

    /** 获取最近交易日 */
    String getMaxTradeDate();
}
