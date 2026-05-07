# CONTRIBUTING — 单人开发（毕业设计） 的 Git 步骤与分支规范

下面把文档精简为针对单人开发（毕业设计）最实用的步骤、命令和建议。文档顶部为简要 checklist，后面给出具体的 PowerShell 可复制命令示例。

Checklist（开始前请确认）
- [ ] 使用单一长期主分支：`main`（作为可交付/答辩演示分支）
- [ ] 所有日常开发在短期分支进行，合并后删除短期分支
- [ ] 在论文提交或答辩前为可交付版本打 tag 并推送到远端
- [ ] 经常 push 到远端做备份（即便单人也要备份）

一、长期分支
- `main`：唯一长期分支，始终保持可演示/可交付状态（用于打 tag）。

二、短期分支命名（建议）
- `feature/<简短描述>` — 新功能，例如 `feature/add-crawler`
- `bugfix/<简短描述>` — 修复问题，例如 `bugfix/fix-npe`
- `wip/<简短描述>` — 长期实验或重构，可以远端备份

三、提交信息规范（简单约定）
- 使用前缀：`feat:`, `fix:`, `docs:`, `chore:` 等
- 示例：`feat: add crawler module`、`fix: handle null pointer in StockService`

四、单人首选工作流（带 PowerShell 命令）

1) 初始化仓库（已有远端请跳过本节）
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

2) 新建短期分支并开发
```powershell
git checkout -b feature/add-crawler
# 修改、测试...
git add .
git commit -m "feat: add basic crawler"
```

3) 在合并前让分支基于最新主干（推荐 rebase 保持线性历史）
```powershell
git fetch origin
git checkout feature/add-crawler
git rebase origin/main
# 若有冲突：编辑文件 -> git add <file> -> git rebase --continue
```

4) 将 feature 合并回 `main`（推荐 squash 合并，保持 `main` 干净）
```powershell
git checkout main
git pull origin main
git merge --squash feature/add-crawler
git commit -m "feat: add basic crawler"
git push origin main
```

5) 合并后删除临时分支（本地与远端）
```powershell
git branch -d feature/add-crawler
git push origin --delete feature/add-crawler
```

五、里程碑与打 tag（答辩/论文提交）
```powershell
git tag -a v0.1.0 -m "论文提交版 2026-05-06"
git push origin v0.1.0
```
在论文或 README 中记录 tag 名称与说明，便于评审复现。

六、常见回滚与恢复（安全方式）
- 已推送但需撤销：使用 git revert <commit>（保留历史并生成反向提交）
- 本地未推的撤销：git reset --soft HEAD~1（保留改动在工作区）或 git reset --hard HEAD~1（不可逆，慎用）

七、临时保存（stash）
```powershell
git stash save "WIP: 描述"
git checkout main
# 恢复
git checkout feature/add-crawler
git stash pop
```

八、实践小技巧
- 频繁小提交并 push（每天或每个子任务后）以降低丢失风险
- 对重要合并使用 PR（即便单人也可在远端创建 PR 来触发 CI，保留记录）
- 在答辩前创建 release 分支或直接打 tag 做快照

九、快速命令速查
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

如果你满意，我可以：
- 1) 再创建一个 `BRANCHING.md`（只保留精简流程和命令摘要）；或
- 2) 生成一个 PowerShell 脚本 `git-helpers.ps1`，把上面常用命令做成几条函数便于执行。

回复 "创建 BRANCHING.md" 或 "创建脚本" 选择下一步。

