package com.stock.controller;

import com.stock.entity.Watchlist;
import com.stock.service.WatchlistService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/watchlist")
public class WatchlistController {

    @Autowired
    private WatchlistService watchlistService;

    @GetMapping("/{userId}")
    public ResponseEntity<List<Watchlist>> list(@PathVariable Long userId,
                                                 @RequestParam(required = false) Integer assetType) {
        return ResponseEntity.ok(watchlistService.getUserWatchlist(userId, assetType));
    }

    @PostMapping("/add")
    public ResponseEntity<?> add(@RequestBody Map<String, Object> params) {
        Long userId = Long.valueOf(params.get("userId").toString());
        String assetCode = params.get("assetCode").toString();
        Integer assetType = Integer.valueOf(params.get("assetType").toString());
        boolean result = watchlistService.addToWatchlist(userId, assetCode, assetType);
        return result ? ResponseEntity.ok(Map.of("message", "添加成功"))
                      : ResponseEntity.badRequest().body(Map.of("error", "已在自选中"));
    }

    @DeleteMapping("/remove")
    public ResponseEntity<?> remove(@RequestParam Long userId,
                                     @RequestParam String assetCode,
                                     @RequestParam Integer assetType) {
        watchlistService.removeFromWatchlist(userId, assetCode, assetType);
        return ResponseEntity.ok(Map.of("message", "删除成功"));
    }
}
