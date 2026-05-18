package com.stock.security;

import java.util.*;
import java.util.stream.Collectors;

/**
 * 权限定义与匹配工具
 * <p>
 * 权限格式: "模块:操作"
 * 支持通配符: "stock:*" 表示股票模块所有权限, "*:*" 表示全部权限
 */
public class Permission {

    private final String module;
    private final String action;
    private final String raw;

    private Permission(String raw) {
        this.raw = raw;
        String[] parts = raw.split(":", 2);
        this.module = parts[0];
        this.action = parts.length > 1 ? parts[1] : "*";
    }

    public String getModule() { return module; }
    public String getAction() { return action; }
    public String getRaw() { return raw; }

    @Override
    public String toString() { return raw; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Permission that)) return false;
        return Objects.equals(raw, that.raw);
    }

    @Override
    public int hashCode() { return Objects.hash(raw); }

    // ============================================================
    // 静态工具方法
    // ============================================================

    /**
     * 将权限字符串解析为 Permission 对象
     */
    public static Permission of(String permission) {
        return new Permission(permission);
    }

    /**
     * 批量解析权限字符串列表
     */
    public static Set<Permission> parseAll(List<String> permissionStrings) {
        if (permissionStrings == null) return Collections.emptySet();
        return permissionStrings.stream()
                .map(Permission::new)
                .collect(Collectors.toSet());
    }

    /**
     * 判断一个权限是否匹配给定的权限集
     * <p>
     * 匹配规则:
     * - "stock:list" 精确匹配 "stock:list"
     * - "stock:*" 通配匹配所有 stock 模块的权限
     * - "*:*" 通配匹配所有权限
     * - "*:read" 通配匹配所有模块的 read 操作
     */
    public boolean matches(Set<Permission> grantedPermissions) {
        for (Permission granted : grantedPermissions) {
            if (matchesSingle(granted)) return true;
        }
        return false;
    }

    /**
     * 判断给定权限集中是否包含此权限
     */
    public boolean matches(Permission granted) {
        return matchesSingle(granted);
    }

    /**
     * 批量判断：检查此权限是否能被权限集覆盖
     */
    public static boolean hasPermission(Set<Permission> grantedPermissions, String required) {
        Permission requiredPerm = new Permission(required);

        // "*:*" 通配所有
        if (grantedPermissions.contains(new Permission("*:*"))) return true;

        for (Permission gp : grantedPermissions) {
            if (requiredPerm.matchesSingle(gp)) return true;
        }
        return false;
    }

    /**
     * 单权限匹配逻辑
     */
    private boolean matchesSingle(Permission granted) {
        // granted "*:*" 匹配所有
        if ("*".equals(granted.module) && "*".equals(granted.action)) return true;

        // granted "stock:*" 匹配所有 stock 操作
        if (granted.module.equals(this.module) && "*".equals(granted.action)) return true;

        // granted "*:read" 匹配所有模块的 read 操作
        if ("*".equals(granted.module) && granted.action.equals(this.action)) return true;

        // 精确匹配
        return granted.module.equals(this.module) && granted.action.equals(this.action);
    }
}
