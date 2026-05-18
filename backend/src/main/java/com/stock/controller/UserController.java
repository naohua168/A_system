package com.stock.controller;

import com.stock.dto.ApiResponse;
import com.stock.entity.User;
import com.stock.security.JwtUtil;
import com.stock.security.UserRole;
import com.stock.service.UserService;
import cn.hutool.crypto.digest.DigestUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/user")
public class UserController {

    @Autowired
    private UserService userService;

    @Autowired
    private JwtUtil jwtUtil;

    /**
     * 修复: 使用 JwtUtil 生成 JWT Token 替代不安全的 MD5 自造 Token
     * 修复: 登录失败返回 ApiResponse 而非原始 ResponseEntity
     */
    @PostMapping("/login")
    public ApiResponse login(@RequestBody Map<String, String> params) {
        String username = params.get("username");
        String password = params.get("password");
        if (username == null || password == null) {
            return ApiResponse.error("用户名和密码不能为空");
        }
        User user = userService.login(username, password);
        if (user != null) {
            // 修复: 使用 JwtUtil 生成符合安全标准的 JWT Token
            String token = jwtUtil.generateToken(user.getId(), user.getUsername(),
                    UserRole.fromLevel(user.getRole()));
            user.setPassword(null);
            Map<String, Object> result = new HashMap<>();
            result.put("token", token);
            result.put("user", user);
            return ApiResponse.ok(result);
        }
        return ApiResponse.error("用户名或密码错误");
    }

    @PostMapping("/register")
    public ApiResponse register(@RequestBody User user) {
        if (user.getPassword() == null || user.getPassword().isBlank()) {
            return ApiResponse.error("密码不能为空");
        }
        if (user.getUsername() == null || user.getUsername().isBlank()) {
            return ApiResponse.error("用户名不能为空");
        }
        user.setPassword(DigestUtil.bcrypt(user.getPassword()));
        userService.save(user);
        return ApiResponse.created("注册成功");
    }

    /**
     * 修复: 从 SecurityContext 获取当前登录用户 ID，而非硬编码 ID=1
     */
    @GetMapping("/info")
    public ApiResponse getInfo() {
        Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        if (principal instanceof String username && !"anonymousUser".equals(username)) {
            User user = userService.getById(
                    ((Number) SecurityContextHolder.getContext().getAuthentication().getCredentials()).longValue());
            if (user != null) {
                user.setPassword(null);
                return ApiResponse.ok(user);
            }
        }
        return ApiResponse.error("未登录");
    }

    @GetMapping("/{id}")
    public ApiResponse getById(@PathVariable Long id) {
        User user = userService.getById(id);
        if (user == null) {
            return ApiResponse.error("用户不存在");
        }
        user.setPassword(null);
        return ApiResponse.ok(user);
    }
}
