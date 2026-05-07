# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Project Overview

## 基金股票智能分析系统

- **Language**: Java 11, Python 3.8, JavaScript (Vue 3)
- **Build tool**: Maven (Backend), Vite (Frontend)
- **Framework**: Spring Boot 2.7.18, Vue 3, Hadoop, Spark
- **Testing Framework**: JUnit, Vue Test Utils

## Architecture

全栈技术架构：
- **前端**: Vue 3 + Vite + Pinia + Vue Router (Apple 设计风格)
- **后端**: Spring Boot + MyBatis Plus + MySQL
- **大数据**: Hadoop + Spark + Hive
- **AI 服务**: Python (缠论分析、技术指标、AI 融合)

## Project Structure

```
F:\bs\A_system
├── frontend/              # Vue 3 前端 (Apple 设计风格)
├── backend/               # Spring Boot 后端
├── ai-service/            # AI 服务 (Python)
├── analysis-algorithms/   # 分析算法 (缠论、技术指标)
├── bigdata-processing/    # 大数据处理 (Hadoop/Spark)
├── data-collector/        # 数据采集
└── docs/                  # 文档
```

## Configuration

The project uses `.env` for frontend configuration and `application.yml` for backend.

## Backing Services

- **Main database**: MySQL 8.0
- **Cache**: Redis
- **Message Queue**: (待配置)
- **Big Data**: Hadoop HDFS, Spark
- **AI Models**: Kimi, 通义千问, 东方财富AI

## Database Naming Convention

- Table Naming: Singular, prefer `account` instead of `accounts`
- 遵循下划线命名法：`user_account`, `stock_data`

## Task Runner

The project uses Maven for backend and npm for frontend:

### Backend (Java)
- Build: `mvn clean package`
- Run: `mvn spring-boot:run`

### Frontend (Vue)
- Install: `npm install`
- Dev: `npm run dev` (http://localhost:3000)
- Build: `npm run build`

### Python Services
- 数据分析: `python analysis-algorithms/chanlun/main.py`
- AI 服务: `python ai-service/app/main.py`

## Development Guidelines

### 前端开发规范 (Apple DESIGN.md)
- 单一 Action Blue (#0066cc) 作为交互色
- SF Pro Display/Text 字体，负字间距
- Tile 交替布局（白色/羊皮纸 ↔ 近黑色）
- 仅产品图片使用阴影
- 严格圆角分级系统
- 禁止使用 emoji 表情，使用 SVG 图标

### 后端开发规范
- RESTful API 设计
- JWT 认证
- 统一响应格式: `{code, message, data}`
- 异常全局处理

## Port Configuration

- **3000**: Frontend web server (Vue dev)
- **8080**: Backend API server (Spring Boot)
- **3306**: MySQL database
- **6379**: Redis cache

## Quick Start

```bash
# 前端
cd frontend
npm install
npm run dev

# 后端
cd backend
mvn spring-boot:run

# 访问
Frontend: http://localhost:3000
Backend API: http://localhost:8080/api
```