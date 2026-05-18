package com.stock.controller;

import com.stock.security.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 安全管理控制器 — 提供安全层级查询、密码策略、账户管理接口
 * 仅 SUPER_ADMIN 可访问
 */
@RestController
@RequestMapping("/api/security")
public class SecurityController {

    @Autowired
    private SecurityLevelService securityLevelService;

    /**
     * 获取所有安全层级定义
     */
    @GetMapping("/levels")
    public ResponseEntity<?> getLevels() {
        return ResponseEntity.ok(securityLevelService.getAllLevels());
    }

    /**
     * 获取指定层级详情
     */
    @GetMapping("/levels/{levelId}")
    public ResponseEntity<?> getLevel(@PathVariable String levelId) {
        var config = securityLevelService.getLevelConfig(levelId.toUpperCase());
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    /**
     * 获取全局安全配置
     */
    @GetMapping("/config")
    public ResponseEntity<?> getGlobalConfig() {
        return ResponseEntity.ok(securityLevelService.getGlobalConfig());
    }

    /**
     * 校验指定角色的权限
     */
    @GetMapping("/permissions/{role}")
    public ResponseEntity<?> getPermissions(@PathVariable String role) {
        UserRole userRole = UserRole.fromConfigId(role.toUpperCase());
        return ResponseEntity.ok(Map.of(
                "role", userRole.getConfigId(),
                "level", userRole.getLevel(),
                "displayName", userRole.getDisplayName(),
                "permissions", securityLevelService.getPermissions(userRole)
                        .stream().map(Permission::toString).toList()
        ));
    }

    /**
     * 批量校验权限
     */
    @PostMapping("/verify")
    public ResponseEntity<?> verifyPermissions(@RequestBody Map<String, Object> params) {
        String roleStr = (String) params.getOrDefault("role", "USER");
        @SuppressWarnings("unchecked")
        List<String> perms = (List<String>) params.getOrDefault("permissions", List.of());
        UserRole role = UserRole.fromConfigId(roleStr.toUpperCase());
        return ResponseEntity.ok(securityLevelService.hasPermissions(role, perms));
    }

    /**
     * 评估密码强度
     */
    @PostMapping("/password-strength")
    public ResponseEntity<?> evaluatePassword(@RequestBody Map<String, String> params) {
        String password = params.get("password");
        String roleStr = params.getOrDefault("role", "USER");
        UserRole role = UserRole.fromConfigId(roleStr.toUpperCase());

        // 获取密码策略
        var policy = securityLevelService.getPasswordPolicy(role);

        // 校验密码是否符合策略
        var validation = PasswordPolicyValidator.validate(password, policy);

        // 评估强度
        var strength = securityLevelService.evaluateStrength(password, role);

        return ResponseEntity.ok(Map.of(
                "valid", validation.isValid(),
                "strength", strength.name(),
                "strengthLabel", getStrengthLabel(strength),
                "errors", validation.getErrors(),
                "policy", Map.of(
                        "minLength", policy.getMinLength(),
                        "maxLength", policy.getMaxLength(),
                        "requireUppercase", policy.isRequireUppercase(),
                        "requireLowercase", policy.isRequireLowercase(),
                        "requireDigit", policy.isRequireDigit(),
                        "requireSpecial", policy.isRequireSpecial(),
                        "maxConsecutiveRepeat", policy.getMaxConsecutiveRepeat()
                )
        ));
    }

    private String getStrengthLabel(SecurityLevelService.PasswordStrength strength) {
        return switch (strength) {
            case WEAK -> "弱";
            case MEDIUM -> "中";
            case STRONG -> "强";
            case VERY_STRONG -> "非常强";
        };
    }
}
