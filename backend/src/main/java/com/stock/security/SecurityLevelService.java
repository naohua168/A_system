package com.stock.security;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import javax.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * 安全层级服务 — 加载并管理 security-levels.yml 配置
 * <p>
 * 提供角色查询、权限验证、密码策略获取等功能。
 * 系统启动时自动加载配置文件并缓存到内存。
 */
@Slf4j
@Service
public class SecurityLevelService {

    /** 安全层级完整配置（从 YAML 解析） */
    private List<SecurityLevelConfig> levelConfigs = new ArrayList<>();

    /** 层级缓存: levelId → SecurityLevelConfig */
    private final Map<String, SecurityLevelConfig> configCache = new ConcurrentHashMap<>();

    /** 权限缓存: levelId → Set<Permission> */
    private final Map<String, Set<Permission>> permissionCache = new ConcurrentHashMap<>();

    /** 全局配置 */
    private Map<String, Object> globalConfig = new HashMap<>();

    /**
     * 初始化加载 YAML 配置
     */
    @PostConstruct
    public void init() {
        try {
            ObjectMapper mapper = new ObjectMapper(new YAMLFactory());
            // 优先从外部配置目录加载，回退到 classpath（classpath 文件已移出构建，参考 docs/security/）
            String externalPath = System.getProperty("security.config.path", "");
            java.io.File externalFile = externalPath.isBlank() ? null : new java.io.File(externalPath);
            if (externalFile != null && externalFile.exists()) {
                try (InputStream is = new java.io.FileInputStream(externalFile)) {
                    loadConfig(mapper, is);
                    return;
                }
            }
            ClassPathResource resource = new ClassPathResource("security/security-levels.yml");

            try (InputStream is = resource.getInputStream()) {
                loadConfig(mapper, is);

                // 解析全局配置
                @SuppressWarnings("unchecked")
                Map<String, Object> global = (Map<String, Object>) root.getOrDefault("global", new HashMap<>());
                this.globalConfig = global;

                // 解析层级配置
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> levels =
                        (List<Map<String, Object>>) root.getOrDefault("levels", new ArrayList<>());

                for (Map<String, Object> levelMap : levels) {
                    SecurityLevelConfig config = parseLevelConfig(levelMap);
                    levelConfigs.add(config);
                    configCache.put(config.getId(), config);
                    permissionCache.put(config.getId(), Permission.parseAll(config.getPermissions()));
                }

                log.info("✅ 安全层级配置加载完成: {} 个层级, {} 条权限规则",
                        levelConfigs.size(),
                        permissionCache.values().stream().mapToInt(Set::size).sum());
            }
        } catch (Exception e) {
            log.error("❌ 安全层级配置加载失败", e);
            // 加载失败时使用默认配置
            loadDefaultConfigs();
        }
    }

    // ============================================================
    // 公共查询方法
    // ============================================================

    /**
     * 获取指定角色的安全层级配置
     */
    public SecurityLevelConfig getConfig(UserRole role) {
        return configCache.getOrDefault(role.getConfigId(),
                SecurityLevelConfig.defaultConfig(role.getConfigId(), role.getDisplayName(), role.getLevel()));
    }

    /**
     * 获取指定角色的密码策略
     */
    public PasswordPolicyValidator.PasswordPolicy getPasswordPolicy(UserRole role) {
        SecurityLevelConfig config = getConfig(role);
        return config.getPasswordPolicy() != null
                ? config.getPasswordPolicy()
                : PasswordPolicyValidator.PasswordPolicy.defaultPolicy();
    }

    /**
     * 获取指定角色的登录策略
     */
    public PasswordPolicyValidator.LoginPolicy getLoginPolicy(UserRole role) {
        SecurityLevelConfig config = getConfig(role);
        return config.getLoginPolicy() != null
                ? config.getLoginPolicy()
                : PasswordPolicyValidator.LoginPolicy.defaultPolicy();
    }

    /**
     * 获取指定角色的权限集
     */
    public Set<Permission> getPermissions(UserRole role) {
        return permissionCache.getOrDefault(role.getConfigId(), Collections.emptySet());
    }

    /**
     * 校验用户是否拥有指定权限
     *
     * @param role          用户角色
     * @param requiredPermission 所需权限字符串 (如 "stock:list")
     * @return true 如果拥有权限
     */
    public boolean hasPermission(UserRole role, String requiredPermission) {
        Set<Permission> granted = getPermissions(role);

        // 超级管理员拥有所有权限
        if (Permission.hasPermission(granted, "*:*")) return true;

        return Permission.hasPermission(granted, requiredPermission);
    }

    /**
     * 批量校验权限
     */
    public Map<String, Boolean> hasPermissions(UserRole role, List<String> requiredPermissions) {
        Map<String, Boolean> result = new LinkedHashMap<>();
        for (String perm : requiredPermissions) {
            result.put(perm, hasPermission(role, perm));
        }
        return result;
    }

    /**
     * 获取所有层级配置（用于管理界面展示）
     */
    public List<SecurityLevelConfig> getAllLevels() {
        return Collections.unmodifiableList(levelConfigs);
    }

    /**
     * 获取指定层级的完整配置
     */
    public SecurityLevelConfig getLevelConfig(String levelId) {
        return configCache.get(levelId);
    }

    /**
     * 获取全局安全设置
     */
    public Map<String, Object> getGlobalConfig() {
        return Collections.unmodifiableMap(globalConfig);
    }

    /**
     * 密码强度评级
     */
    public enum PasswordStrength {
        WEAK,       // 仅满足最低要求
        MEDIUM,     // 满足最低要求 + 额外1项
        STRONG,     // 满足该层级全部要求
        VERY_STRONG // 超过该层级要求
    }

    /**
     * 评估密码强度
     */
    public PasswordStrength evaluateStrength(String password, UserRole role) {
        SecurityLevelConfig config = getConfig(role);
        PasswordPolicyValidator.PasswordPolicy policy = config.getPasswordPolicy();
        ValidationResult result = PasswordPolicyValidator.validate(password, policy);

        if (!result.isValid()) return PasswordStrength.WEAK;

        // 计数额外满足的条件
        int extras = 0;
        int length = password.length();
        if (length > policy.getMaxLength() - 5) extras++;
        if (password.chars().filter(Character::isUpperCase).count() > 2) extras++;
        if (password.chars().filter(c -> !Character.isLetterOrDigit(c)).count() > 2) extras++;

        if (extras >= 2) return PasswordStrength.VERY_STRONG;
        if (extras >= 1) return PasswordStrength.STRONG;
        return PasswordStrength.MEDIUM;
    }

    // ============================================================
    // 私有方法
    // ============================================================

    @SuppressWarnings("unchecked")
    private SecurityLevelConfig parseLevelConfig(Map<String, Object> levelMap) {
        SecurityLevelConfig config = new SecurityLevelConfig();
        config.setId((String) levelMap.getOrDefault("id", "USER"));
        config.setName((String) levelMap.getOrDefault("name", "普通用户"));
        config.setLevel((Integer) levelMap.getOrDefault("level", 1));
        config.setDescription((String) levelMap.getOrDefault("description", ""));

        // 权限列表
        config.setPermissions((List<String>) levelMap.getOrDefault("permissions", new ArrayList<>()));

        // 密码策略
        Map<String, Object> pwdMap = (Map<String, Object>) levelMap.getOrDefault("password_policy", new HashMap<>());
        PasswordPolicyValidator.PasswordPolicy pwdPolicy = new PasswordPolicyValidator.PasswordPolicy();
        if (pwdMap.containsKey("min_length")) pwdPolicy.setMinLength((Integer) pwdMap.get("min_length"));
        if (pwdMap.containsKey("max_length")) pwdPolicy.setMaxLength((Integer) pwdMap.get("max_length"));
        if (pwdMap.containsKey("require_uppercase")) pwdPolicy.setRequireUppercase((Boolean) pwdMap.get("require_uppercase"));
        if (pwdMap.containsKey("require_lowercase")) pwdPolicy.setRequireLowercase((Boolean) pwdMap.get("require_lowercase"));
        if (pwdMap.containsKey("require_digit")) pwdPolicy.setRequireDigit((Boolean) pwdMap.get("require_digit"));
        if (pwdMap.containsKey("require_special")) pwdPolicy.setRequireSpecial((Boolean) pwdMap.get("require_special"));
        if (pwdMap.containsKey("max_consecutive_repeat")) pwdPolicy.setMaxConsecutiveRepeat((Integer) pwdMap.get("max_consecutive_repeat"));
        if (pwdMap.containsKey("expiry_days")) pwdPolicy.setExpiryDays((Integer) pwdMap.get("expiry_days"));
        if (pwdMap.containsKey("history_count")) pwdPolicy.setHistoryCount((Integer) pwdMap.get("history_count"));
        config.setPasswordPolicy(pwdPolicy);

        // 登录策略
        Map<String, Object> loginMap = (Map<String, Object>) levelMap.getOrDefault("login_policy", new HashMap<>());
        PasswordPolicyValidator.LoginPolicy loginPolicy = new PasswordPolicyValidator.LoginPolicy();
        if (loginMap.containsKey("max_retry")) loginPolicy.setMaxRetry((Integer) loginMap.get("max_retry"));
        if (loginMap.containsKey("lockout_minutes")) loginPolicy.setLockoutMinutes((Integer) loginMap.get("lockout_minutes"));
        if (loginMap.containsKey("session_timeout_minutes")) loginPolicy.setSessionTimeoutMinutes((Integer) loginMap.get("session_timeout_minutes"));
        if (loginMap.containsKey("max_sessions")) loginPolicy.setMaxSessions((Integer) loginMap.get("max_sessions"));
        if (loginMap.containsKey("require_mfa")) loginPolicy.setRequireMfa((Boolean) loginMap.get("require_mfa"));
        config.setLoginPolicy(loginPolicy);

        return config;
    }

    /** 加载 YAML 配置流 */
    @SuppressWarnings("unchecked")
    private void loadConfig(ObjectMapper mapper, InputStream is) throws Exception {
        Map<String, Object> root = mapper.readValue(is, new TypeReference<>() {});

        // 解析全局配置
        Map<String, Object> global = (Map<String, Object>) root.getOrDefault("global", new HashMap<>());
        this.globalConfig = global;

        // 解析层级配置
        List<Map<String, Object>> levels =
                (List<Map<String, Object>>) root.getOrDefault("levels", new ArrayList<>());

        for (Map<String, Object> levelMap : levels) {
            SecurityLevelConfig config = parseLevelConfig(levelMap);
            levelConfigs.add(config);
            configCache.put(config.getId(), config);
            permissionCache.put(config.getId(), Permission.parseAll(config.getPermissions()));
        }

        log.info("✅ 安全层级配置加载完成: {} 个层级, {} 条权限规则",
                levelConfigs.size(),
                permissionCache.values().stream().mapToInt(Set::size).sum());
    }

    private void loadDefaultConfigs() {
        SecurityLevelConfig defaultConfig = SecurityLevelConfig.defaultConfig("USER", "普通用户", 1);
        levelConfigs.add(defaultConfig);
        configCache.put("USER", defaultConfig);
        permissionCache.put("USER", Permission.parseAll(defaultConfig.getPermissions()));
        log.warn("使用默认安全层级配置");
    }
}
