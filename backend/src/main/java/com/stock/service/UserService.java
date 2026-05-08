package com.stock.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.stock.entity.User;

public interface UserService extends IService<User> {
    User login(String username, String password);
}
