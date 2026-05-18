package com.stock.security;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * 密码策略校验器
 * <p>
 * 根据 security-levels.yml 中定义的密码策略，校验密码复杂度。
 * 不同角色适用不同的密码策略强度。
 */
public class PasswordPolicyValidator {

    /** 密码策略配置 */
    @Data
    public static class PasswordPolicy {
        private int minLength = 8;
        private int maxLength = 32;
        private boolean requireUppercase = true;
        private boolean requireLowercase = true;
        private boolean requireDigit = true;
        private boolean requireSpecial = false;
        private int maxConsecutiveRepeat = 3;
        private int expiryDays = 90;
        private int historyCount = 3;

        public static PasswordPolicy defaultPolicy() {
            return new PasswordPolicy();
        }
    }

    /** 登录策略配置 */
    @Data
    public static class LoginPolicy {
        private int maxRetry = 5;
        private int lockoutMinutes = 30;
        private int sessionTimeoutMinutes = 60;
        private int maxSessions = 2;
        private boolean requireMfa = false;

        public static LoginPolicy defaultPolicy() {
            return new LoginPolicy();
        }
    }

    /** 安全层级全量配置（对应 YAML 中的单个 level） */
    @Data
    public static class SecurityLevelConfig {
        private String id;
        private String name;
        private int level;
        private String description;
        private PasswordPolicy passwordPolicy = PasswordPolicy.defaultPolicy();
        private LoginPolicy loginPolicy = LoginPolicy.defaultPolicy();
        private List<String> permissions = new ArrayList<>();

        /** 创建默认配置 */
        public static SecurityLevelConfig defaultConfig(String id, String name, int level) {
            SecurityLevelConfig config = new SecurityLevelConfig();
            config.setId(id);
            config.setName(name);
            config.setLevel(level);
            config.setDescription("默认安全配置");
            config.setPasswordPolicy(PasswordPolicy.defaultPolicy());
            config.setLoginPolicy(LoginPolicy.defaultPolicy());
            return config;
        }
    }

    /** 校验结果 */
    @Data
    public static class ValidationResult {
        private boolean valid;
        private List<String> errors = new ArrayList<>();

        public static ValidationResult success() {
            ValidationResult r = new ValidationResult();
            r.valid = true;
            return r;
        }

        public static ValidationResult failure(List<String> errors) {
            ValidationResult r = new ValidationResult();
            r.valid = false;
            r.errors = errors;
            return r;
        }
    }

    // ── 正则表达式 ──
    private static final Pattern UPPERCASE_PATTERN = Pattern.compile("[A-Z]");
    private static final Pattern LOWERCASE_PATTERN = Pattern.compile("[a-z]");
    private static final Pattern DIGIT_PATTERN = Pattern.compile("[0-9]");
    private static final Pattern SPECIAL_PATTERN = Pattern.compile("[!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>/?]");

    /**
     * 校验密码是否符合指定层级的密码策略
     *
     * @param password   待校验密码
     * @param policy     密码策略
     * @return 校验结果
     */
    public static ValidationResult validate(String password, PasswordPolicy policy) {
        if (policy == null) policy = PasswordPolicy.defaultPolicy();
        List<String> errors = new ArrayList<>();

        if (password == null || password.isEmpty()) {
            errors.add("密码不能为空");
            return ValidationResult.failure(errors);
        }

        // 长度检查
        if (password.length() < policy.getMinLength()) {
            errors.add(String.format("密码长度不能少于 %d 位", policy.getMinLength()));
        }
        if (password.length() > policy.getMaxLength()) {
            errors.add(String.format("密码长度不能超过 %d 位", policy.getMaxLength()));
        }

        // 大写字母
        if (policy.isRequireUppercase() && !UPPERCASE_PATTERN.matcher(password).find()) {
            errors.add("密码必须包含至少 1 个大写字母");
        }

        // 小写字母
        if (policy.isRequireLowercase() && !LOWERCASE_PATTERN.matcher(password).find()) {
            errors.add("密码必须包含至少 1 个小写字母");
        }

        // 数字
        if (policy.isRequireDigit() && !DIGIT_PATTERN.matcher(password).find()) {
            errors.add("密码必须包含至少 1 个数字");
        }

        // 特殊字符
        if (policy.isRequireSpecial() && !SPECIAL_PATTERN.matcher(password).find()) {
            errors.add("密码必须包含至少 1 个特殊字符 (!@#$%^&*等)");
        }

        // 连续重复字符
        int maxRepeat = policy.getMaxConsecutiveRepeat();
        if (maxRepeat > 0) {
            int repeat = 1;
            for (int i = 1; i < password.length(); i++) {
                if (password.charAt(i) == password.charAt(i - 1)) {
                    repeat++;
                    if (repeat > maxRepeat) {
                        errors.add(String.format("密码不能包含超过 %d 个连续相同字符", maxRepeat));
                        break;
                    }
                } else {
                    repeat = 1;
                }
            }
        }

        if (errors.isEmpty()) {
            return ValidationResult.success();
        }
        return ValidationResult.failure(errors);
    }

    /**
     * 快速判断密码是否满足策略
     */
    public static boolean isSatisfiedBy(String password, PasswordPolicy policy) {
        return validate(password, policy).isValid();
    }
}
