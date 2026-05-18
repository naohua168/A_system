package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoGlobalNews;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoGlobalNewsMapper extends BaseMapper<InfoGlobalNews> {

    @Select("SELECT * FROM info_global_news ORDER BY publish_time DESC LIMIT #{limit}")
    List<InfoGlobalNews> selectLatest(@Param("limit") int limit);
}
