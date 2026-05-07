# CONTRIBUTING — 1周冲锋（毕业设计）的 Git 步骤与分支规范

本文档为单人开发（毕业设计）提供最实用的 Git 步骤、命令和建议。配合 **1周MVP冲锋计划**，每天完成多个模块的并行开发。

---

## Checklist（开始前请确认）

- [ ] 使用单一长期主分支：`main`（作为可交付/答辩演示分支）
- [ ] 所有日常开发在短期分支进行，合并后删除短期分支
- [ ] 在答辩前为可交付版本打 tag 并推送到远端
- [ ] **每天结束时 push 一次**，降低数据丢失风险

---

## 1周冲锋计划的Git节奏

| 天 | 当天开发模块 | 分支命名建议 | 提交策略 |
|:--:|:------------|:------------|:---------|
| Day 1 | Docker + 后端骨架 + 前端初始化 | `feature/env-setup` | 每个子任务一个commit |
| Day 2 | 数据采集 + Hive + CRUD API | `feature/data-channel` | 早/中各一次commit, 晚上merge |
| Day 3 | MapReduce + Spark + 分析API | `feature/bigdata-processing` | 同上 |
| Day 4 | 缠论 + 技术指标 + 量化 | `feature/analysis-algorithms` | 同上 |
| Day 5 | K线图 + 股票列表 + 基金页面 | `feature/frontend-stock` | 同上 |
| Day 6 | AI服务 + 前后端联调 | `feature/ai-integration` | 同上 |
| Day 7 | 测试 + 文档 + 演示 | `feature/final-polish` | 所有修复+文档 |

> **Git提交节奏**: 每个模块完成后立即提交（不必等到一天结束），避免代码丢失。

---

## 一、长期分支

- `main`：唯一长期分支，始终保持可演示/可交付状态（用于打 tag）。

## 二、短期分支命名（建议）

- `feature/<简短描述>` — 新功能，例如 `feature/add-crawler`
- `bugfix/<简短描述>` — 修复问题，例如 `bugfix/fix-npe`
- `wip/<简短描述>` — 长期实验或重构，可以远端备份

## 三、提交信息规范（简单约定）

- 使用前缀：`feat:`, `fix:`, `docs:`, `chore:` 等
- 示例：`feat: add crawler module`、`fix: handle null pointer in StockService`

## 四、单人首选工作流（带 PowerShell 命令）

### 1) 初始化仓库（已有远端请跳过本节）

```powershell
git init
echo "# 项目名" > README.md
echo "bin/" > .gitignore
git add README.md .gitignore
git commit -m "chore: init repository"
git branch -M main
git remote add origin <你的远端仓库地址>
git push -u origin main
```

### 2) 新建短期分支并开发

```powershell
git checkout -b feature/add-crawler
# 修改、测试...
git add .
git commit -m "feat: add basic crawler"
```

### 3) 在合并前让分支基于最新主干（推荐 rebase 保持线性历史）

```powershell
git fetch origin
git checkout feature/add-crawler
git rebase origin/main
# 若有冲突：编辑文件 -> git add <file> -> git rebase --continue
```

### 4) 将 feature 合并回 `main`（推荐 squash 合并，保持 `main` 干净）

```powershell
git checkout main
git pull origin main
git merge --squash feature/add-crawler
git commit -m "feat: add basic crawler"
git push origin main
```

### 5) 合并后删除临时分支（本地与远端）

```powershell
git branch -d feature/add-crawler
git push origin --delete feature/add-crawler
```

## 五、里程碑与打 tag（答辩/论文提交）

```powershell
# 1周冲锋各阶段里程碑
git tag -a v0.1.0 -m "Day1: 环境基石就绪 2026-05-07"
git tag -a v0.2.0 -m "Day2: 数据通道打通 2026-05-08"
git tag -a v0.3.0 -m "Day3: 大数据处理完成 2026-05-09"
git tag -a v0.4.0 -m "Day4: 分析算法就绪 2026-05-10"
git tag -a v0.5.0 -m "Day5: 前端展示完成 2026-05-11"
git tag -a v0.6.0 -m "Day6: AI集成+全链路打通 2026-05-12"
git tag -a v1.0.0 -m "1周冲锋交付版 2026-05-13"

# 推送所有tag
git push origin --tags
```

在论文或 README 中记录 tag 名称与说明，便于评审复现。

## 六、常见回滚与恢复（安全方式）

- 已推送但需撤销：使用 `git revert <commit>`（保留历史并生成反向提交）
- 本地未推的撤销：`git reset --soft HEAD~1`（保留改动在工作区）或 `git reset --hard HEAD~1`（不可逆，慎用）

## 七、临时保存（stash）

```powershell
git stash save "WIP: 描述"
git checkout main
# 恢复
git checkout feature/add-crawler
git stash pop
```

## 八、实践小技巧（针对1周冲锋）

- **每天至少 push 一次** — 1周高强度的开发中，代码安全第一
- **每个子任务一个 commit** — 方便后续回溯和论文中描述实现过程
- **Day 1 就创建一个完整分支** `feature/env-setup`，不要等
- **睡前务必 squash merge 到 main**，保证第二天从干净的主线开始
- **Day 7 打 v1.0.0 tag** 后，不要再修改 main

## 九、快速命令速查

```powershell
# 创建并切换分支
git checkout -b feature/xxx

# 推送并设置上游
git push -u origin feature/xxx

# 同步主干并 rebase
git fetch origin
git rebase origin/main

# squash 合并到 main
git checkout main
git merge --squash feature/xxx
git commit -m "feat: ..."

# 删除分支
git branch -d feature/xxx
git push origin --delete feature/xxx

# 打 tag 并推送
git tag -a v0.1.0 -m "desc"
git push origin v0.1.0
```

---

## 附录：各模块对应的分支命名速查表

| 模块 | 分支名 | 开发工具 |
|:----|:-------|:--------|
| Docker环境 | `feature/env-setup` | 任意文本编辑器 |
| 数据采集 | `feature/data-collector` | PyCharm |
| Hive建表 | `feature/hive-schema` | DataGrip |
| MapReduce | `feature/mapreduce` | IntelliJ IDEA |
| Spark脚本 | `feature/spark-jobs` | PyCharm |
| Spring Boot后端 | `feature/backend-api` | IntelliJ IDEA |
| Vue 3前端 | `feature/frontend-ui` | Code Buddy |
| 缠论算法 | `feature/chanlun` | PyCharm |
| AI服务 | `feature/ai-service` | PyCharm |
| 测试修复 | `bugfix/xxx` | 视模块而定 |
| 文档完善 | `docs/xxx` | 任意文本编辑器 |
