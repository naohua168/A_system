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
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.*;
import java.util.stream.Collectors;

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

    @Autowired
    private JdbcTemplate jdbcTemplate;

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

        // 批量查询基金净值（用于计算 navDate 和 yearReturn）
        List<Map<String, Object>> enriched = new ArrayList<>();
        if (!p.getRecords().isEmpty()) {
            List<String> fundCodes = p.getRecords().stream()
                .map(Fund::getFundCode).collect(Collectors.toList());

            List<FundNav> navs = fundNavService.list(
                new LambdaQueryWrapper<FundNav>()
                    .in(FundNav::getFundCode, fundCodes)
                    .orderByDesc(FundNav::getNavDate)
            );

            // 按 fundCode 分组: fundCode -> [navDate -> nav]
            Map<String, List<FundNav>> navByCode = navs.stream()
                .collect(Collectors.groupingBy(FundNav::getFundCode));

            // 批量查询货币基金7日年化
            String inClause = fundCodes.stream().map(c -> "'" + c + "'").collect(Collectors.joining(","));
            Map<String, Map<String, Object>> moneyMarketMap = new HashMap<>();
            try {
                List<Map<String, Object>> mmRows = jdbcTemplate.queryForList(
                    "SELECT fund_code, seven_day_yield, daily_return, monthly_return, yearly_return_14d, " +
                    "yearly_return_28d, quarter_return, half_year_return, year_return " +
                    "FROM fund_money_market WHERE fund_code IN (" + inClause + ")");
                for (Map<String, Object> row : mmRows) {
                    moneyMarketMap.put((String) row.get("fund_code"), row);
                }
            } catch (Exception ignored) {}

            // 批量查询 ETF 行情
            Map<String, Map<String, Object>> etfMarketMap = new HashMap<>();
            try {
                List<Map<String, Object>> etfRows = jdbcTemplate.queryForList(
                    "SELECT fund_code, price, change_pct, volume, amount " +
                    "FROM fund_etf_market WHERE fund_code IN (" + inClause + ")");
                for (Map<String, Object> row : etfRows) {
                    etfMarketMap.put((String) row.get("fund_code"), row);
                }
            } catch (Exception ignored) {}

            for (Fund fund : p.getRecords()) {
                Map<String, Object> map = new LinkedHashMap<>();
                map.put("id", fund.getId());
                map.put("fundCode", fund.getFundCode());
                map.put("fundName", fund.getFundName());
                map.put("fundType", fund.getFundType());
                map.put("nav", fund.getNav());
                map.put("accumulatedNav", fund.getAccumulatedNav());
                map.put("company", fund.getCompany());
                map.put("manager", fund.getManager());
                map.put("establishDate", fund.getEstablishDate() != null ? fund.getEstablishDate().toString() : null);
                map.put("scale", fund.getScale());

                // 判断是否货币基金（用万份收益模式，不适合单位净值计算收益）
                boolean isMoneyMarket = fund.getFundType() != null
                    && (fund.getFundType().contains("货币") || fund.getFundType().contains("货币型"));

                String navDate = "";
                Double yearReturn = null;
                Integer returnDays = null;
                List<FundNav> fundNavs = navByCode.get(fund.getFundCode());

                if (isMoneyMarket) {
                    // 货币基金：使用 fund_money_market 数据
                    map.put("nav", null);
                    map.put("yearReturn", null);
                    map.put("returnDays", null);
                    map.put("navDate", "");
                    map.put("isMoneyMarket", true);
                    Map<String, Object> mm = moneyMarketMap.get(fund.getFundCode());
                    if (mm != null) {
                        map.put("sevenDayYield", mm.get("seven_day_yield"));
                        map.put("dailyReturnMoney", mm.get("daily_return"));
                        map.put("monthReturnMoney", mm.get("monthly_return"));
                        map.put("yearReturnMoney", mm.get("year_return"));
                    }
                } else if (fundNavs != null && !fundNavs.isEmpty()) {
                    // 非货币基金且有NAV数据：正常计算阶段收益
                    FundNav latest = fundNavs.get(0);
                    navDate = latest.getNavDate() != null ? latest.getNavDate().toString() : "";

                    FundNav oldest = fundNavs.get(fundNavs.size() - 1);
                    if (oldest.getNav() != null && oldest.getNavDate() != null
                            && latest.getNav() != null && latest.getNavDate() != null) {
                        long daysBetween = latest.getNavDate().toEpochDay() - oldest.getNavDate().toEpochDay();
                        returnDays = (int) daysBetween;
                        if (fundNavs.size() >= 2 && daysBetween >= 1
                                && oldest.getNav().compareTo(BigDecimal.ZERO) > 0) {
                            yearReturn = latest.getNav().subtract(oldest.getNav())
                                .divide(oldest.getNav(), 6, java.math.RoundingMode.HALF_UP)
                                .multiply(BigDecimal.valueOf(100))
                                .setScale(2, java.math.RoundingMode.HALF_UP)
                                .doubleValue();
                        }
                    }
                    map.put("navDate", navDate);
                    map.put("yearReturn", yearReturn);
                    map.put("returnDays", returnDays);
                    map.put("isMoneyMarket", false);
                } else {
                    // 无NAV数据（后端基金/定开债等）
                    map.put("navDate", "");
                    map.put("yearReturn", null);
                    map.put("returnDays", null);
                    map.put("isMoneyMarket", false);
                }
                enriched.add(map);
            }
        }
        return ApiResponse.page(enriched, p.getTotal(), page, size);
    }

    @GetMapping("/{code}")
    public ApiResponse getByCode(@PathVariable String code) {
        LambdaQueryWrapper<Fund> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Fund::getFundCode, code);
        Fund fund = fundService.getOne(wrapper);
        if (fund == null) {
            return ApiResponse.notFound("基金不存在: " + code);
        }
        // 包装返回，标记货币基金
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", fund.getId());
        map.put("fundCode", fund.getFundCode());
        map.put("fundName", fund.getFundName());
        map.put("fundType", fund.getFundType());
        map.put("company", fund.getCompany());
        map.put("manager", fund.getManager());
        map.put("establishDate", fund.getEstablishDate() != null ? fund.getEstablishDate().toString() : null);
        map.put("scale", fund.getScale());
        map.put("nav", fund.getNav());
        map.put("accumulatedNav", fund.getAccumulatedNav());

        boolean isMoneyMarket = fund.getFundType() != null
            && (fund.getFundType().contains("货币") || fund.getFundType().contains("货币型"));
        map.put("isMoneyMarket", isMoneyMarket);
        if (isMoneyMarket) {
            map.put("nav", null);
            try {
                Map<String, Object> mm = jdbcTemplate.queryForMap(
                    "SELECT seven_day_yield, daily_return, monthly_return, year_return " +
                    "FROM fund_money_market WHERE fund_code = ?", code);
                map.put("sevenDayYield", mm.get("seven_day_yield"));
                map.put("dailyReturnMoney", mm.get("daily_return"));
                map.put("monthReturnMoney", mm.get("monthly_return"));
                map.put("yearReturnMoney", mm.get("year_return"));
            } catch (Exception ignored) {}
        }
        // 查询 ETF 行情
        try {
            Map<String, Object> etf = jdbcTemplate.queryForMap(
                "SELECT price, change_pct, volume, amount FROM fund_etf_market WHERE fund_code = ?", code);
            map.put("etfPrice", etf.get("price"));
            map.put("etfChangePct", etf.get("change_pct"));
        } catch (Exception ignored) {}
        return ApiResponse.ok(map);
    }

    @GetMapping("/{code}/nav")
    public ApiResponse navHistory(@PathVariable String code,
                                  @RequestParam(defaultValue = "30") int days) {
        List<FundNav> list = fundNavService.getLatest(code, days);
        return list.isEmpty() ? ApiResponse.ok(java.util.Collections.emptyList()) : ApiResponse.ok(list);
    }

    @GetMapping("/nav/{code}")
    public ApiResponse navHistoryAlt(@PathVariable String code,
                                     @RequestParam(defaultValue = "30") int days) {
        return navHistory(code, days);
    }

    @GetMapping("/{code}/holdings")
    public ApiResponse getHoldings(@PathVariable String code) {
        List<FundHolding> holdings = fundHoldingService.getTopHoldings(code, 10);
        return holdings.isEmpty() ? ApiResponse.ok(java.util.Collections.emptyList()) : ApiResponse.ok(holdings);
    }
}
