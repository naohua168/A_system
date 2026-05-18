package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoClsNews;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoClsNewsMapper extends BaseMapper<InfoClsNews> {

    @Select("SELECT * FROM info_cls_news ORDER BY publish_time DESC LIMIT #{limit}")
    List<InfoClsNews> selectLatest(@Param("limit") int limit);

    @Select("SELECT * FROM info_cls_news WHERE publish_time >= #{since} ORDER BY publish_time DESC")
    List<InfoClsNews> selectSince(@Param("since") String since);
}
