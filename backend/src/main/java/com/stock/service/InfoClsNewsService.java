package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoClsNews;

import java.util.List;

public interface InfoClsNewsService extends IService<InfoClsNews> {
    List<InfoClsNews> getLatest(int limit);
    List<InfoClsNews> getSince(String since);
}
