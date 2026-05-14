package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.PrecomputedResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface PrecomputedResultMapper extends BaseMapper<PrecomputedResult> {

    /** 查询指定年份排名前N的股票 */
    @Select("SELECT * FROM precomputed_yearly_return WHERE year = #{year} AND rank <= #{topN} ORDER BY rank ASC")
    List<PrecomputedResult> selectTopByYear(@Param("year") int year, @Param("topN") int topN);

    /** 查询指定年份某只股票的年化收益 */
    @Select("SELECT * FROM precomputed_yearly_return WHERE year = #{year} AND stock_code = #{stockCode} LIMIT 1")
    PrecomputedResult selectByStockAndYear(@Param("stockCode") String stockCode, @Param("year") int year);

    /** 查询某只股票所有年份的年化收益 */
    @Select("SELECT * FROM precomputed_yearly_return WHERE stock_code = #{stockCode} ORDER BY year DESC")
    List<PrecomputedResult> selectByStock(@Param("stockCode") String stockCode);
}
