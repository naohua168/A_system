package com.stock.controller;

import com.stock.entity.Fund;
import com.stock.entity.FundNav;
import com.stock.mapper.FundNavMapper;
import com.stock.service.FundService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/fund")
public class FundController {

    @Autowired
    private FundService fundService;

    @Autowired
    private FundNavMapper fundNavMapper;

    @GetMapping("/list")
    public ResponseEntity<?> list(@RequestParam(defaultValue = "1") int page,
                                  @RequestParam(defaultValue = "20") int size,
                                  @RequestParam(required = false) String keyword,
                                  @RequestParam(required = false) String fundType) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Fund> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        if (keyword != null) {
            wrapper.like(Fund::getFundName, keyword)
                   .or().like(Fund::getFundCode, keyword);
        }
        if (fundType != null) {
            wrapper.eq(Fund::getFundType, fundType);
        }
        com.baomidou.mybatisplus.core.metadata.IPage<Fund> p =
                fundService.page(new com.baomidou.mybatisplus.extension.plugins.pagination.Page<>(page, size), wrapper);
        return ResponseEntity.ok(Map.of("records", p.getRecords(), "total", p.getTotal(), "page", page, "size", size));
    }

    @GetMapping("/{code}")
    public ResponseEntity<?> getByCode(@PathVariable String code) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Fund> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(Fund::getFundCode, code);
        Fund fund = fundService.getOne(wrapper);
        if (fund == null) {
            return ResponseEntity.status(404).body(Map.of("error", "基金不存在"));
        }
        return ResponseEntity.ok(fund);
    }

    // 兼容两种路径：前端调 /api/fund/{code}/nav，后端已有 /api/fund/nav/{code}
    @GetMapping("/{code}/nav")
    public ResponseEntity<List<FundNav>> navHistoryByCode(@PathVariable String code,
                                                           @RequestParam(defaultValue = "30") int days) {
        return navHistory(code, days);
    }

    @GetMapping("/nav/{code}")
    public ResponseEntity<List<FundNav>> navHistory(@PathVariable String code,
                                                     @RequestParam(defaultValue = "30") int days) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<FundNav> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(FundNav::getFundCode, code);
        wrapper.orderByDesc(FundNav::getNavDate);
        wrapper.last("LIMIT " + days);
        List<FundNav> list = fundNavMapper.selectList(wrapper);
        java.util.Collections.reverse(list);
        return ResponseEntity.ok(list);
    }

    @GetMapping("/{code}/holdings")
    public ResponseEntity<?> getHoldings(@PathVariable String code) {
        // 返回示例持仓数据（无持仓表时返回空列表）
        return ResponseEntity.ok(Collections.emptyList());
    }
}
