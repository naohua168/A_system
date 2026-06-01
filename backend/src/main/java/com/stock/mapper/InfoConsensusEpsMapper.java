package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.InfoConsensusEps;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InfoConsensusEpsMapper extends BaseMapper<InfoConsensusEps> {

    @Select("SELECT * FROM info_consensus_eps WHERE stock_code = #{code} ORDER BY year DESC LIMIT 10")
    List<InfoConsensusEps> selectByStock(@Param("code") String code);

    @Select("SELECT * FROM info_consensus_eps WHERE stock_code = #{code} AND year = #{year} LIMIT 1")
    InfoConsensusEps selectByStockAndYear(@Param("code") String code, @Param("year") String year);
}
