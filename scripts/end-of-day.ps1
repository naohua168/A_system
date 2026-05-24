<#
.SYNOPSIS
    安全关闭开发环境并结束当日工作流程
.DESCRIPTION
    自动保存状态 → 停服务 → 检查 → 提交 → 输出摘要
#>

# ---------- 配置 ----------
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$GitRepoDir = $ProjectRoot
$CommitMsg = "daily-work: $(Get-Date -Format 'yyyy-MM-dd') end of day"
$StartTimeFile = Join-Path $ProjectRoot ".session_start"
$WorkspaceStateFile = Join-Path $ProjectRoot ".workspace_state"

# ---------- 颜色输出 ----------
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Blue }
function Write-OK    { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }
function Write-Step { Write-Host "`n══════ $args ══════" -ForegroundColor Cyan }

# ---------- 记录运行时长 ----------
$SessionDuration = "unknown"
if (Test-Path $StartTimeFile) {
    $StartEpoch = [long](Get-Content $StartTimeFile -Raw).Trim()
    $NowEpoch = [long](Get-Date -UFormat %s)
    $Elapsed = $NowEpoch - $StartEpoch
    $Hours = [math]::Floor($Elapsed / 3600)
    $Minutes = [math]::Floor(($Elapsed % 3600) / 60)
    $SessionDuration = "${Hours}h ${Minutes}m"
}

# ---------- 1. 环境检查 ----------
function Step-CheckEnvironment {
    Write-Step "Step 1: 环境检查"

    # 检查 Git 仓库
    try {
        $null = git -C $GitRepoDir rev-parse --git-dir 2>&1
        Write-OK "Git 仓库验证通过"
    } catch {
        Write-Error "当前目录不是一个 Git 仓库"
        exit 1
    }

    # 检查合并冲突
    $conflicts = git -C $GitRepoDir diff --name-only --diff-filter=U 2>$null
    if ($conflicts) {
        Write-Error "存在未解决的合并冲突:"
        $conflicts | ForEach-Object { Write-Host "    - $_" }
        exit 1
    }
    Write-OK "无未解决的合并冲突"

    # 检查未追踪文件
    $untracked = git -C $GitRepoDir ls-files --others --exclude-standard 2>$null
    if ($untracked) {
        Write-Warn "发现未追踪的新文件:"
        $untracked | ForEach-Object { Write-Host "    - $_" }
        Write-Host ""
    } else {
        Write-OK "无未追踪文件"
    }
}

# ---------- 2. 保存工作区状态 ----------
function Step-SaveWorkspace {
    Write-Step "Step 2: 保存工作区状态"

    $branch = git -C $GitRepoDir rev-parse --abbrev-ref HEAD 2>$null
    $hash = git -C $GitRepoDir rev-parse HEAD 2>$null
    @"
branch=$branch
saved_at=$(Get-Date -Format o)
git_hash=$hash
"@ | Set-Content $WorkspaceStateFile -Encoding UTF8

    Write-OK "工作区状态已保存 (.workspace_state)"
}

# ---------- 3. 终止本地服务 ----------
function Step-StopServices {
    Write-Step "Step 3: 终止本地服务"

    $FreedPorts = @()

    # 终止 Vite 节点进程
    $viteProcs = Get-Process -Name "node" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "vite" -or $_.CommandLine -match "stock-analysis-frontend" }
    if ($viteProcs) {
        $viteProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-OK "Vite 开发服务器已停止"
        $FreedPorts += 5173
    } else {
        Write-Info "Vite 开发服务器未运行"
    }

    # 终止本地 Java 后端进程
    $javaProcs = Get-Process -Name "java" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "stock-analysis-backend" }
    if ($javaProcs) {
        $javaProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-OK "本地 Java 后端进程已停止"
        $FreedPorts += 8082
    }

    # 终止本地 Python 进程
    $pythonProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "uvicorn" -or $_.CommandLine -match "ai-service" }
    if ($pythonProcs) {
        $pythonProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-OK "本地 Python 服务已停止"
        $FreedPorts += 8000
    }

    # 检查端口释放
    Write-Info "检查端口释放状态..."
    @(5173, 8082, 8000) | ForEach-Object {
        $conn = Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue
        if ($conn) {
            Write-Warn "端口 $_ 仍被占用 ($($conn.State))"
        } else {
            Write-OK "端口 $_ 已释放"
        }
    }

    if ($FreedPorts.Count -gt 0) {
        Write-Info "释放的端口: $($FreedPorts -join ', ')"
    }
}

# ---------- 4. 暂存并提交 ----------
$Script:CommitCount = 0
$Script:ChangedFiles = 0
$Script:Insertions = 0
$Script:Deletions = 0

function Step-GitCommit {
    Write-Step "Step 4: 提交代码变更"

    # 暂存所有变更
    git -C $GitRepoDir add -A 2>$null

    # 检查是否有变更
    $hasChanges = git -C $GitRepoDir diff --cached --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Info "工作区干净，无变更需要提交"
        return
    }

    # 统计变更
    $diffStat = git -C $GitRepoDir diff --cached --shortstat 2>$null
    $Script:ChangedFiles = (git -C $GitRepoDir diff --cached --name-only 2>$null | Measure-Object).Count

    if ($diffStat -match '(\d+) insertion') { $Script:Insertions = $Matches[1] }
    if ($diffStat -match '(\d+) deletion')  { $Script:Deletions  = $Matches[1] }

    # 执行提交
    git -C $GitRepoDir commit -m $CommitMsg
    if ($LASTEXITCODE -eq 0) {
        $Script:CommitCount = 1
        Write-OK "提交成功: $CommitMsg"
        Write-Info "  变更文件: $ChangedFiles | +$Insertions/-$Deletions"
    } else {
        Write-Error "提交失败"
        exit 1
    }
}

# ---------- 5. 输出摘要 ----------
function Step-PrintSummary {
    Write-Step "Step 5: 工作结束摘要"

    $branch = git -C $GitRepoDir rev-parse --abbrev-ref HEAD 2>$null
    $lastCommit = git -C $GitRepoDir log -1 --format='%h %s' 2>$null

    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║         今日工作已安全结束                 ║" -ForegroundColor Cyan
    Write-Host "  ╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  📅 日期:       $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    Write-Host "  🌿 分支:       $branch"
    Write-Host "  ⏱  运行时长:   $SessionDuration"
    Write-Host "  📝 提交次数:   $CommitCount"
    if ($ChangedFiles -gt 0) {
        Write-Host "  📂 变更文件:   $ChangedFiles (+$Insertions/-$Deletions)"
    }
    Write-Host "  💾 最后提交:   $lastCommit"
    Write-Host ""
    Write-Host "  🟢 所有服务已停止，端口已释放" -ForegroundColor Green
    Write-Host "  🟢 Git 工作区已提交" -ForegroundColor Green
    Write-Host "  🟢 可安全关闭 IDE" -ForegroundColor Green
    Write-Host ""
}

# ---------- 主流程 ----------
function Main {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "     🔒 安全关闭开发环境" -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host ""

    Step-CheckEnvironment
    Step-SaveWorkspace
    Step-StopServices
    Step-GitCommit
    Step-PrintSummary

    # 清理临时文件
    Remove-Item $WorkspaceStateFile -Force -ErrorAction SilentlyContinue
    Remove-Item $StartTimeFile -Force -ErrorAction SilentlyContinue
}

Main
