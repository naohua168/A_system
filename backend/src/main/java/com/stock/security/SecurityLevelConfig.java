package com.stock.security;

import lombok.Data;

import java.util.Collections;
import java.util.List;

/**
 * 安全层级配置 — 从 security-levels.yml 解析
 *
 * 包含角色基本信息、权限列表、密码策略和登录策略。
 */
@Data
public class SecurityLevelConfig {

    /** 层级标识 (如 "USER", "ADMIN", "SUPER_ADMIN") */
    private String id;

    /** 层级显示名称 */
    private String name;

    /** 层级数值 (1=最低, 4=最高) */
    private int level;

    /** 层级描述 */
    private String description;

    /** 权限列表 (如 "stock:list", "analysis:*") */
    private List<String> permissions = Collections.emptyList();

    /** 密码策略 */
    private PasswordPolicyValidator.PasswordPolicy passwordPolicy;

    /** 登录策略 */
    private PasswordPolicyValidator.LoginPolicy loginPolicy;

    /** 创建默认配置 */
    public static SecurityLevelConfig defaultConfig(String id, String name, int level) {
        SecurityLevelConfig config = new SecurityLevelConfig();
        config.setId(id);
        config.setName(name);
        config.setLevel(level);
        config.setDescription("默认安全层级");
        config.setPermissions(List.of("*:read"));
        config.setPasswordPolicy(PasswordPolicyValidator.PasswordPolicy.defaultPolicy());
        config.setLoginPolicy(PasswordPolicyValidator.LoginPolicy.defaultPolicy());
        return config;
    }
}
