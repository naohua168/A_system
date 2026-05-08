package com.stock.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.stock.entity.User;
import com.stock.mapper.UserMapper;
import com.stock.service.UserService;
import cn.hutool.crypto.digest.DigestUtil;
import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @Override
    public User login(String username, String password) {
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(User::getUsername, username);
        User user = baseMapper.selectOne(wrapper);
        if (user != null && DigestUtil.bcryptCheck(password, user.getPassword())) {
            return user;
        }
        return null;
    }
}
