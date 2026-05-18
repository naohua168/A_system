package com.stock.security;

import java.lang.annotation.*;

/**
 * 权限检查注解 — 用于 Controller 方法级别的细粒度权限控制
 * <p>
 * 用法：
 * <pre>
 * {@code @RequirePermission("stock:list")}
 * public ResponseEntity<?> listStocks() { ... }
 *
 * {@code @RequirePermission(value = "user:delete", role = UserRole.SUPER_ADMIN)}
 * public ResponseEntity<?> deleteUser() { ... }
 * </pre>
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RequirePermission {

    /**
     * 所需权限，格式 "模块:操作"，如 "stock:list", "admin:*"
     */
    String value();

    /**
     * 所需最低角色级别（可选，默认不限制）
     */
    UserRole role() default UserRole.USER;

    /**
     * 拒绝时的错误消息
     */
    String message() default "权限不足，拒绝访问";
}
