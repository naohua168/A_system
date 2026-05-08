package com.stock.controller;

import com.stock.entity.AnalysisResult;
import com.stock.mapper.AnalysisResultMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    @Autowired
    private AnalysisResultMapper analysisResultMapper;

    @GetMapping("/{assetCode}")
    public ResponseEntity<List<AnalysisResult>> getAnalysis(@PathVariable String assetCode,
                                                             @RequestParam(required = false) String type) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<AnalysisResult> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(AnalysisResult::getAssetCode, assetCode);
        if (type != null) {
            wrapper.eq(AnalysisResult::getAnalysisType, type);
        }
        wrapper.orderByDesc(AnalysisResult::getAnalysisDate);
        return ResponseEntity.ok(analysisResultMapper.selectList(wrapper));
    }
}
