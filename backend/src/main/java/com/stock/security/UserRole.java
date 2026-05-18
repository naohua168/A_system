package com.stock.security;

import java.util.Arrays;
import java.util.List;

/**
 * 用户角色枚举 — 对应 security-levels.yml 中的层级定义
 */
public enum UserRole {

    USER(1, "普通用户", "USER"),
    PREMIUM_USER(2, "高级用户", "PREMIUM_USER"),
    ADMIN(3, "管理员", "ADMIN"),
    SUPER_ADMIN(4, "超级管理员", "SUPER_ADMIN");

    /** 安全层级数值 (1-4, 越高权限越大) */
    private final int level;

    /** 中文名称 */
    private final String displayName;

    /** 配置中的 ID 标识 */
    private final String configId;

    UserRole(int level, String displayName, String configId) {
        this.level = level;
        this.displayName = displayName;
        this.configId = configId;
    }

    public int getLevel() { return level; }
    public String getDisplayName() { return displayName; }
    public String getConfigId() { return configId; }

    /**
     * 从整数值查找到对应角色
     */
    public static UserRole fromLevel(Integer level) {
        if (level == null) return USER;
        return Arrays.stream(values())
                .filter(r -> r.level == level)
                .findFirst()
                .orElse(USER);
    }

    /**
     * 从配置 ID 查找角色
     */
    public static UserRole fromConfigId(String configId) {
        return Arrays.stream(values())
                .filter(r -> r.configId.equalsIgnoreCase(configId))
                .findFirst()
                .orElse(USER);
    }

    /**
     * 当前角色是否包含指定的权限（基于层级级别判断）
     * 低层级不能访问高层级资源
     */
    public boolean canAccess(UserRole requiredRole) {
        return this.level >= requiredRole.level;
    }

    /**
     * 获取所有低于或等于当前级别的角色
     */
    public List<UserRole> getInclusiveRoles() {
        return Arrays.stream(values())
                .filter(r -> r.level <= this.level)
                .toList();
    }

    /**
     * 判断是否为管理角色
     */
    public boolean isAdmin() {
        return this == ADMIN || this == SUPER_ADMIN;
    }
}
