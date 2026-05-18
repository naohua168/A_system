package com.stock.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.stock.security.UserRole;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user")
public class User {

    // ============================================================
    // 基础字段
    // ============================================================
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 用户名（唯一） */
    private String username;

    /** 密码哈希值（BCrypt） */
    private String password;

    /** 电子邮箱 */
    private String email;

    /** 手机号 */
    private String phone;

    /** 头像URL */
    private String avatar;

    // ============================================================
    // 安全层级字段
    // ============================================================

    /**
     * 用户角色级别
     * 1=普通用户(USER), 2=高级用户(PREMIUM_USER),
     * 3=管理员(ADMIN), 4=超级管理员(SUPER_ADMIN)
     */
    private Integer role;

    /** 用户状态: 0=正常, 1=禁用, 2=锁定 */
    private Integer status;

    /** 是否启用多因素认证 */
    private Boolean mfaEnabled;

    /** 密码最后修改时间（用于过期检测） */
    private LocalDateTime passwordChangedAt;

    /** 密码过期时间 */
    private LocalDateTime passwordExpiresAt;

    /** 最后登录时间 */
    private LocalDateTime lastLoginAt;

    /** 连续登录失败次数 */
    private Integer failedLoginAttempts;

    /** 账户锁定截止时间（null 表示未锁定） */
    private LocalDateTime lockedUntil;

    // ============================================================
    // 审计字段
    // ============================================================

    /** 创建者用户名 */
    private String createdBy;

    /** 创建时间 */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    /** 更新时间 */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    // ============================================================
    // 便捷方法
    // ============================================================

    /** 获取枚举角色 */
    public UserRole getUserRole() {
        return UserRole.fromLevel(this.role);
    }

    /** 设置枚举角色 */
    public void setUserRole(UserRole userRole) {
        this.role = userRole.getLevel();
    }

    /** 账户是否被锁定 */
    public boolean isLocked() {
        if (lockedUntil == null) return false;
        return LocalDateTime.now().isBefore(lockedUntil);
    }

    /** 密码是否已过期 */
    public boolean isPasswordExpired() {
        if (passwordExpiresAt == null) return false;
        return LocalDateTime.now().isAfter(passwordExpiresAt);
    }

    /** 账户是否激活 */
    public boolean isActive() {
        return status != null && status == 0;
    }
}
