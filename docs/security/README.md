# 安全凭据参考文档

> **⚠️ 重要安全警告**: 此目录中的文件**仅供开发人员参考**，**不打包到 JAR 中**。
> 生产环境请使用环境变量或密钥管理服务（如 Vault）注入凭据。

## 文件说明

| 文件名 | 用途 | 安全要求 |
|--------|------|----------|
| `credentials.json` | 系统凭据总览（账户、基础设施、JWT 密钥） | 生产环境必须修改所有默认凭据 |
| `security-accounts.json` | 用户种子数据（BCrypt 哈希后的密码） | 仅用于初始化数据库，**包含密码哈希** |
| `security-levels.yml` | 安全层级配置文件（密码策略、权限矩阵） | 可根据业务需求调整 |

## 凭据配置方式

所有敏感凭据应通过**环境变量**注入，而非硬编码在代码中：

```bash
# 后端数据库
DB_PASSWORD=your_secure_password

# AI 服务（建议使用硅基流动 SiliconFlow）
SILICONFLOW_API_KEY=your_siliconflow_api_key
SILICONFLOW_MODEL=Qwen/Qwen2.5-72B-Instruct
# 备用 DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key

# MySQL 根密码（Docker）
MYSQL_ROOT_PASSWORD=your_root_password

# JWT 密钥（生产环境必须更换）
JWT_SECRET=your_64_character_random_secret
```

## 变更记录

- 2026-05-18: 从 `backend/src/main/resources/security/` 迁移到 `docs/security/`
  - 防止凭据文件被意外打包到 JAR 包中
  - 移除 `security-accounts.json` 中的 `plaintext_hint` 明文密码提示字段
