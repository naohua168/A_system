package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.Watchlist;

import java.util.List;

public interface WatchlistService extends IService<Watchlist> {
    List<Watchlist> getUserWatchlist(Long userId, Integer assetType);
    boolean addToWatchlist(Long userId, String assetCode, Integer assetType);
    boolean removeFromWatchlist(Long userId, String assetCode, Integer assetType);
}
