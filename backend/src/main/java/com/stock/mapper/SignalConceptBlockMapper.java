package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.SignalConceptBlock;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface SignalConceptBlockMapper extends BaseMapper<SignalConceptBlock> {

    @Select("SELECT * FROM signal_concept_block WHERE stock_code = #{code} AND block_type = #{type}")
    List<SignalConceptBlock> selectByStockAndType(@Param("code") String code, @Param("type") String type);

    @Select("SELECT * FROM signal_concept_block WHERE stock_code = #{code}")
    List<SignalConceptBlock> selectByStock(@Param("code") String code);
}
