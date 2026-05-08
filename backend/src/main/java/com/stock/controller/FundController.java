package com.stock.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.stock.entity.Fund;
import com.stock.entity.FundNav;
import com.stock.mapper.FundNavMapper;
import com.stock.service.FundService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/fund")
public class FundController {

    @Autowired
    private FundService fundService;

    @Autowired
    private FundNavMapper fundNavMapper;

    @GetMapping("/list")
    public ResponseEntity<IPage<Fund>> list(@RequestParam(defaultValue = "1") int page,
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
        return ResponseEntity.ok(fundService.page(new Page<>(page, size), wrapper));
    }

    @GetMapping("/{code}")
    public ResponseEntity<Fund> getByCode(@PathVariable String code) {
        LambdaQueryWrapper<Fund> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Fund::getFundCode, code);
        return ResponseEntity.ok(fundService.getOne(wrapper));
    }

    @GetMapping("/nav/{code}")
    public ResponseEntity<List<FundNav>> navHistory(@PathVariable String code,
                                                     @RequestParam(defaultValue = "30") int days) {
        LambdaQueryWrapper<FundNav> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(FundNav::getFundCode, code);
        wrapper.orderByDesc(FundNav::getNavDate);
        wrapper.last("LIMIT " + days);
        List<FundNav> list = fundNavMapper.selectList(wrapper);
        java.util.Collections.reverse(list);
        return ResponseEntity.ok(list);
    }
}
