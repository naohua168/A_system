package com.stock.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.stock.dto.ApiResponse;
import com.stock.entity.Fund;
import com.stock.entity.FundHolding;
import com.stock.entity.FundNav;
import com.stock.service.FundHoldingService;
import com.stock.service.FundNavService;
import com.stock.service.FundService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 基金层控制器 — 不再直接注入 Mapper
 *
 * 新架构:
 *   data-collector → akshare_ext → MySQL(fund/fund_nav/fund_holding)
 *   前端从此 API 读取
 *
 * 路由前缀: /api/fund
 */
@RestController
@RequestMapping("/api/fund")
public class FundController {

    @Autowired
    private FundService fundService;

    @Autowired
    private FundNavService fundNavService;

    @Autowired
    private FundHoldingService fundHoldingService;

    @GetMapping("/list")
    public ApiResponse list(@RequestParam(defaultValue = "1") int page,
                            @RequestParam(defaultValue = "20") int size,
                            @RequestParam(required = false) String keyword,
                            @RequestParam(required = false) String fundType) {
        LambdaQueryWrapper<Fund> wrapper = new LambdaQueryWrapper<>();
        if (keyword != null) {
            wrapper.like(Fund::getFundName, keyword)
                   .or().like(Fund::getFundCode, keyword);
        }
        if (fundType != null) {
            wrapper.eq(Fund::getFundType, fundType);
        }
        Page<Fund> p = fundService.page(new Page<>(page, size), wrapper);
        return ApiResponse.page(p.getRecords(), p.getTotal(), page, size);
    }

    @GetMapping("/{code}")
    public ApiResponse getByCode(@PathVariable String code) {
        LambdaQueryWrapper<Fund> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Fund::getFundCode, code);
        Fund fund = fundService.getOne(wrapper);
        if (fund == null) {
            return ApiResponse.notFound("基金不存在: " + code);
        }
        return ApiResponse.ok(fund);
    }

    @GetMapping("/{code}/nav")
    public ApiResponse navHistory(@PathVariable String code,
                                  @RequestParam(defaultValue = "30") int days) {
        List<FundNav> list = fundNavService.getLatest(code, days);
        return list.isEmpty() ? ApiResponse.error("无净值数据") : ApiResponse.ok(list);
    }

    @GetMapping("/nav/{code}")
    public ApiResponse navHistoryAlt(@PathVariable String code,
                                     @RequestParam(defaultValue = "30") int days) {
        return navHistory(code, days);
    }

    @GetMapping("/{code}/holdings")
    public ApiResponse getHoldings(@PathVariable String code) {
        List<FundHolding> holdings = fundHoldingService.getTopHoldings(code, 10);
        return holdings.isEmpty() ? ApiResponse.error("无持仓数据") : ApiResponse.ok(holdings);
    }
}
