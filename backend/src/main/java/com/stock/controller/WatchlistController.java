package com.stock.controller;

import com.stock.entity.Watchlist;
import com.stock.service.WatchlistService;
import javax.validation.Valid;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Positive;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/watchlist")
public class WatchlistController {

    private static final Logger log = LoggerFactory.getLogger(WatchlistController.class);

    private final WatchlistService watchlistService;

    public WatchlistController(WatchlistService watchlistService) {
        this.watchlistService = watchlistService;
    }

    /** 自选添加请求 DTO */
    public record AddRequest(
            @NotNull @Positive Long userId,
            @NotBlank String assetCode,
            @NotNull @Positive Integer assetType
    ) {}

    /** 自选删除请求 DTO */
    public record RemoveRequest(
            @NotNull @Positive Long userId,
            @NotBlank String assetCode,
            @NotNull @Positive Integer assetType
    ) {}

    /** 自选更新请求 DTO（新增） */
    public record UpdateRequest(
            @NotNull @Positive Long id,
            String remark,
            Integer sortOrder
    ) {}

    @GetMapping("/{userId}")
    public ResponseEntity<List<Watchlist>> list(@PathVariable @Positive Long userId,
                                                 @RequestParam(required = false) @Positive Integer assetType) {
        return ResponseEntity.ok(watchlistService.getUserWatchlist(userId, assetType));
    }

    @PostMapping("/add")
    public ResponseEntity<?> add(@RequestBody AddRequest req) {
        boolean result = watchlistService.addToWatchlist(req.userId, req.assetCode, req.assetType);
        return result ? ResponseEntity.ok(Map.of("message", "添加成功"))
                      : ResponseEntity.badRequest().body(Map.of("error", "已在自选中"));
    }

    @DeleteMapping("/remove")
    public ResponseEntity<?> remove(@RequestBody RemoveRequest req) {
        try {
            watchlistService.removeFromWatchlist(req.userId, req.assetCode, req.assetType);
            return ResponseEntity.ok(Map.of("message", "删除成功"));
        } catch (Exception e) {
            log.warn("自选删除失败 userId={} assetCode={}: {}", req.userId, req.assetCode, e.getMessage());
            return ResponseEntity.badRequest().body(Map.of("error", "删除失败，请检查参数"));
        }
    }

    // ==================== 新增 PUT 端点 ====================

    @PutMapping("/update")
    public ResponseEntity<?> update(@RequestBody @Valid UpdateRequest req) {
        Watchlist item = watchlistService.getById(req.id());
        if (item == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "自选记录不存在"));
        }
        if (req.remark() != null) {
            item.setRemark(req.remark());
        }
        if (req.sortOrder() != null) {
            item.setSortOrder(req.sortOrder());
        }
        watchlistService.updateById(item);
        return ResponseEntity.ok(Map.of("message", "更新成功", "data", item));
    }
}
