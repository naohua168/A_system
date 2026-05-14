package com.stock.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.stock.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface UserMapper extends BaseMapper<User> {

    /** 用户信息更新（选择性更新） */
    int updateUserInfo(@Param("id") Long id,
                       @Param("username") String username,
                       @Param("email") String email,
                       @Param("phone") String phone,
                       @Param("avatar") String avatar);

    /** 按用户名查询 */
    User selectByUsername(@Param("username") String username);

    /** 查询用户角色 */
    Integer selectUserRole(@Param("id") Long id);
}
