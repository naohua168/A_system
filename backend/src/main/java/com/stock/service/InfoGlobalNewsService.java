package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.InfoGlobalNews;

import java.util.List;

public interface InfoGlobalNewsService extends IService<InfoGlobalNews> {
    List<InfoGlobalNews> getLatest(int limit);
}
