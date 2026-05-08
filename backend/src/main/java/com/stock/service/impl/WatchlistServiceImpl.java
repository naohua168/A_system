package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.Watchlist;
import com.stock.mapper.WatchlistMapper;
import com.stock.service.WatchlistService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class WatchlistServiceImpl extends ServiceImpl<WatchlistMapper, Watchlist> implements WatchlistService {

    @Override
    public List<Watchlist> getUserWatchlist(Long userId, Integer assetType) {
        LambdaQueryWrapper<Watchlist> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Watchlist::getUserId, userId);
        if (assetType != null) {
            wrapper.eq(Watchlist::getAssetType, assetType);
        }
        wrapper.orderByAsc(Watchlist::getSortOrder);
        return baseMapper.selectList(wrapper);
    }

    @Override
    public boolean addToWatchlist(Long userId, String assetCode, Integer assetType) {
        LambdaQueryWrapper<Watchlist> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Watchlist::getUserId, userId)
               .eq(Watchlist::getAssetCode, assetCode)
               .eq(Watchlist::getAssetType, assetType);
        if (baseMapper.selectCount(wrapper) > 0) {
            return false;
        }
        Watchlist item = new Watchlist();
        item.setUserId(userId);
        item.setAssetCode(assetCode);
        item.setAssetType(assetType);
        return save(item);
    }

    @Override
    public boolean removeFromWatchlist(Long userId, String assetCode, Integer assetType) {
        LambdaQueryWrapper<Watchlist> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Watchlist::getUserId, userId)
               .eq(Watchlist::getAssetCode, assetCode)
               .eq(Watchlist::getAssetType, assetType);
        return baseMapper.delete(wrapper) > 0;
    }
}
