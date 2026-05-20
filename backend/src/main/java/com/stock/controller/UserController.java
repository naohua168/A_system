package com.stock.controller;

import com.stock.dto.ApiResponse;
import com.stock.entity.User;
import com.stock.security.JwtUtil;
import com.stock.security.UserRole;
import com.stock.service.UserService;
import cn.hutool.crypto.digest.DigestUtil;
import javax.validation.Valid;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/api/user")
public class UserController {

    @Autowired
    private UserService userService;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired(required = false)
    private StringRedisTemplate redisTemplate;

    // ==================== 认证 ====================

    @PostMapping("/login")
    public ApiResponse login(@RequestBody Map<String, String> params) {
        String username = params.get("username");
        String password = params.get("password");
        if (username == null || password == null) {
            return ApiResponse.error("用户名和密码不能为空");
        }
        User user = userService.login(username, password);
        if (user != null) {
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

    // ==================== 用户信息 ====================

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

    // ==================== 更新用户（新增 PUT） ====================

    /** 更新用户信息请求 DTO */
    public record UpdateUserRequest(
            String email,
            String phone,
            String avatar,
            String username
    ) {}

    @PutMapping("/update")
    public ApiResponse updateUser(@RequestBody @Valid UpdateUserRequest request) {
        Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        if (!(principal instanceof String) || "anonymousUser".equals(principal)) {
            return ApiResponse.error("未登录");
        }
        Long userId = ((Number) SecurityContextHolder.getContext().getAuthentication().getCredentials()).longValue();
        User user = userService.getById(userId);
        if (user == null) {
            return ApiResponse.error("用户不存在");
        }

        User updateEntity = new User();
        updateEntity.setId(userId);
        if (request.email() != null) updateEntity.setEmail(request.email());
        if (request.phone() != null) updateEntity.setPhone(request.phone());
        if (request.avatar() != null) updateEntity.setAvatar(request.avatar());
        if (request.username() != null) updateEntity.setUsername(request.username());
        userService.updateById(updateEntity);

        User updated = userService.getById(userId);
        updated.setPassword(null);
        return ApiResponse.ok(updated);
    }

    // ==================== 密码修改（新增 POST） ====================

    public record ChangePasswordRequest(
            @NotBlank String oldPassword,
            @NotBlank @Size(min = 6) String newPassword
    ) {}

    @PostMapping("/change-password")
    public ApiResponse changePassword(@RequestBody @Valid ChangePasswordRequest request) {
        Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        if (!(principal instanceof String) || "anonymousUser".equals(principal)) {
            return ApiResponse.error("未登录");
        }
        Long userId = ((Number) SecurityContextHolder.getContext().getAuthentication().getCredentials()).longValue();
        User user = userService.getById(userId);
        if (user == null) {
            return ApiResponse.error("用户不存在");
        }
        if (!DigestUtil.bcryptCheck(request.oldPassword(), user.getPassword())) {
            return ApiResponse.error("原密码错误");
        }
        user.setPassword(DigestUtil.bcrypt(request.newPassword()));
        userService.updateById(user);
        return ApiResponse.ok("密码修改成功");
    }

    // ==================== Token 管理（新增 POST） ====================

    @PostMapping("/logout")
    public ApiResponse logout(@RequestHeader("Authorization") String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ApiResponse.error("无效的 Token");
        }
        String token = authHeader.substring(7);
        try {
            long remainingTtl = jwtUtil.validateToken(token).getExpiration().getTime() - System.currentTimeMillis();
            if (remainingTtl > 0 && redisTemplate != null) {
                redisTemplate.opsForValue().set("blacklist:" + token, "1",
                        remainingTtl, TimeUnit.MILLISECONDS);
            }
        } catch (Exception ignored) {
            // Token 已过期无需加入黑名单
        }
        return ApiResponse.ok("已登出");
    }

    @PostMapping("/refresh")
    public ApiResponse refreshToken(@RequestHeader("Authorization") String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ApiResponse.error("无效的 Token");
        }
        String token = authHeader.substring(7);
        try {
            // 检查黑名单
            if (redisTemplate != null && Boolean.TRUE.equals(
                    redisTemplate.hasKey("blacklist:" + token))) {
                return ApiResponse.error("Token 已失效");
            }

            var claims = jwtUtil.validateToken(token);
            Long userId = Long.parseLong(claims.getSubject());
            String username = claims.get("username", String.class);
            String roleStr = claims.get("role", String.class);

            String newToken = jwtUtil.generateToken(userId, username,
                    UserRole.fromConfigId(roleStr));
            return ApiResponse.ok(Map.of("token", newToken));
        } catch (Exception e) {
            return ApiResponse.error("Token 无效或已过期");
        }
    }
}
