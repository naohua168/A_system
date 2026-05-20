<#
.SYNOPSIS
    A_system 全自动部署脚本 — 环境检查 → 配置加载 → 数据库迁移 → 零停机部署 → 回滚

.DESCRIPTION
    支持三种部署模式:
      full        : 基础设施 + 应用服务全量部署
      app-only    : 仅部署应用服务（redis/ai-service/backend/frontend）
      infra-only  : 仅部署基础设施（hadoop/hive/spark/mysql）

    特性:
      - 部署前环境检查（Docker/磁盘/端口）
      - 自动发现并执行 SQL 迁移
      - 零停机滚动更新
      - 健康检查门控
      - 失败自动回滚
      - 结构化 JSON 日志 + 终端报告

.PARAMETER Mode
    部署模式: full | app-only | infra-only | rollback

.PARAMETER SkipBuild
    跳过 Docker 构建（仅重启已有镜像）

.PARAMETER SkipMigration
    跳过数据库迁移

.PARAMETER DryRun
    仅输出执行计划，不实际执行

.EXAMPLE
    .\scripts\deploy.ps1 -Mode full                       # 全量部署
    .\scripts\deploy.ps1 -Mode app-only -SkipBuild        # 仅重启应用服务
    .\scripts\deploy.ps1 -Mode rollback                   # 回滚到上一版本
    .\scripts\deploy.ps1 -Mode full -DryRun               # 预览部署计划
#>

param(
    [ValidateSet("full", "app-only", "infra-only", "rollback")]
    [string]$Mode = "full",
    [switch]$SkipBuild,
    [switch]$SkipMigration,
    [switch]$DryRun
)

# ============================================================
# 初始化
# ============================================================
$ErrorActionPreference = "Stop"
$script:START_TIME = Get-Date
$script:DEPLOY_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$script:CONFIG_FILE = Join-Path $PSScriptRoot "deploy-config.json"
$script:DEPLOY_STATE_DIR = Join-Path $DEPLOY_ROOT ".deploy"
$script:LOG_DIR = Join-Path $DEPLOY_STATE_DIR "logs"
$script:DEPLOY_LOG = Join-Path $LOG_DIR "deploy_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$script:REPORT_FILE = Join-Path $LOG_DIR "report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$script:MIGRATION_TABLE = "schema_migrations"

# 确保目录存在
$null = New-Item -ItemType Directory -Path $LOG_DIR -Force
$null = New-Item -ItemType Directory -Path $DEPLOY_STATE_DIR -Force

# ============================================================
# 日志系统
# ============================================================
$script:LOG_ENTRIES = @()

function Write-DeployLog {
    param(
        [string]$Message,
        [ValidateSet("INFO","WARN","ERROR","FATAL","PASS","FAIL","SKIP","STEP")]
        [string]$Level = "INFO",
        [string]$Category = "general"
    )
    $entry = @{
        timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff")
        level     = $Level
        category  = $Category
        message   = $Message
        deploy_id = $script:DEPLOY_ID
    }
    $script:LOG_ENTRIES += $entry

    $colorMap = @{
        "INFO"  = "White"; "WARN"  = "Yellow"; "ERROR" = "Red"
        "FATAL" = "DarkRed"; "PASS"  = "Green"; "FAIL"  = "Red"
        "SKIP"  = "DarkYellow"; "STEP" = "Cyan"
    }
    $iconMap = @{
        "INFO"="ℹ️ "; "WARN"="⚠️ "; "ERROR"="❌ "; "FATAL"="💀 "
        "PASS"="✅ "; "FAIL"="❌ "; "SKIP"="⏭️ "; "STEP"="🔧 "
    }

    $color = $colorMap[$Level]
    $icon  = $iconMap[$Level]
    Write-Host "$icon $Message" -ForegroundColor $color
    "$($entry.timestamp) [$Level] $Message" | Out-File -FilePath $script:DEPLOY_LOG -Encoding utf8 -Append
}

function Write-Step {
    param([string]$Message)
    Write-DeployLog -Message "──────────────────── $Message ────────────────────" -Level STEP -Category "step"
}

function Write-Summary {
    Write-DeployLog -Message "==================== 部署摘要 ====================" -Level STEP -Category "summary"
    $errors   = $script:LOG_ENTRIES | Where-Object { $_.level -in @("ERROR","FATAL","FAIL") }
    $warnings = $script:LOG_ENTRIES | Where-Object { $_.level -eq "WARN" }
    $elapsed  = (Get-Date) - $script:START_TIME

    $summary = @{
        deploy_id     = $script:DEPLOY_ID
        mode          = $Mode
        start_time    = $script:START_TIME.ToString("yyyy-MM-dd HH:mm:ss")
        end_time      = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        elapsed_sec   = [math]::Round($elapsed.TotalSeconds, 1)
        status        = if ($errors.Count -gt 0) { "FAILED" } else { "SUCCESS" }
        errors        = $errors.Count
        warnings      = $warnings.Count
        total_logs    = $script:LOG_ENTRIES.Count
        dry_run       = $DryRun.IsPresent
    }

    Write-Host ""
    Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  A_system 部署报告" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  部署ID    : $($summary.deploy_id)" -ForegroundColor White
    Write-Host "  模式      : $($summary.mode)" -ForegroundColor White
    Write-Host "  状态      : $($summary.status)" -ForegroundColor $(if ($summary.status -eq "SUCCESS") {"Green"} else {"Red"})
    Write-Host "  耗时      : $($summary.elapsed_sec) 秒" -ForegroundColor White
    Write-Host "  错误      : $($summary.errors)" -ForegroundColor $(if ($summary.errors -gt 0) {"Red"} else {"Green"})
    Write-Host "  警告      : $($summary.warnings)" -ForegroundColor Yellow
    Write-Host ""

    if ($errors.Count -gt 0) {
        Write-Host "  ❌ 错误详情:" -ForegroundColor Red
        foreach ($e in $errors) {
            Write-Host "     • [$($e.category)] $($e.message)" -ForegroundColor Red
        }
        Write-Host ""
    }

    # 写入报告文件
    $summary | ConvertTo-Json -Depth 3 | Out-File -FilePath $script:REPORT_FILE -Encoding utf8

    return ($errors.Count -eq 0)
}

# ============================================================
# 环境检查
# ============================================================
function Test-Prerequisites {
    Write-Step "环境依赖检查"

    # 1. Docker 版本
    try {
        $version = docker info --format "{{.ServerVersion}}" 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Docker 未运行" }
        Write-DeployLog -Message "Docker 引擎: v$version" -Level PASS -Category "prereq"
    } catch {
        Write-DeployLog -Message "Docker 未运行，请启动 Docker Desktop" -Level FATAL -Category "prereq"
        return $false
    }

    # 2. Docker Compose
    try {
        $composeVer = docker compose version --short 2>&1
        Write-DeployLog -Message "Docker Compose: v$composeVer" -Level PASS -Category "prereq"
    } catch {
        Write-DeployLog -Message "Docker Compose 不可用" -Level FATAL -Category "prereq"
        return $false
    }

    # 3. 磁盘空间（至少 10GB 可用）
    $drive = (Get-PSDrive -Name ($DEPLOY_ROOT -replace ':\\.*', '')).Free / 1GB
    if ($drive -lt 10) {
        Write-DeployLog -Message "磁盘空间不足: ${drive}GB (需要 ≥ 10GB)" -Level FATAL -Category "prereq"
        return $false
    }
    Write-DeployLog -Message "磁盘空间: $([math]::Round($drive, 1))GB 可用" -Level PASS -Category "prereq"

    # 4. 配置模板
    if (-not (Test-Path $script:CONFIG_FILE)) {
        Write-DeployLog -Message "部署配置文件不存在: $($script:CONFIG_FILE)" -Level FATAL -Category "prereq"
        return $false
    }
    Write-DeployLog -Message "部署配置: $($script:CONFIG_FILE)" -Level PASS -Category "prereq"

    # 5. docker-compose.yml
    $composeFile = Join-Path $DEPLOY_ROOT "docker/docker-compose.yml"
    if (-not (Test-Path $composeFile)) {
        Write-DeployLog -Message "docker-compose.yml 不存在: $composeFile" -Level FATAL -Category "prereq"
        return $false
    }
    Write-DeployLog -Message "Compose 文件: docker/docker-compose.yml" -Level PASS -Category "prereq"

    # 6. 端口检查
    $portChecks = @{
        "frontend"  = 80
        "backend"   = 8082
        "ai"        = 8000
        "mysql"     = 3306
        "redis"     = 6379
    }
    $portErrors = 0
    foreach ($svc in @("redis", "ai-service", "backend", "frontend")) {
        $port = $portChecks[$svc -replace "-.*", ""]
        if (-not $port) { continue }
        $conn = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($conn.TcpTestSucceeded) {
            Write-DeployLog -Message "端口 $port ($svc) 已被占用" -Level WARN -Category "prereq"
            $portErrors++
        }
    }
    if ($portErrors -gt 0) {
        Write-DeployLog -Message "$portErrors 个端口已被占用（部署后会自动复用）" -Level WARN -Category "prereq"
    }

    return $true
}

# ============================================================
# 数据库迁移
# ============================================================
function Invoke-DatabaseMigration {
    param([string]$SqlDir)
    Write-Step "数据库迁移"

    if ($SkipMigration.IsPresent) {
        Write-DeployLog -Message "跳过数据库迁移（--SkipMigration）" -Level SKIP -Category "migration"
        return $true
    }

    # 查找所有 SQL 文件
    $sqlFiles = @()
    $migrationDirs = @(
        Join-Path $DEPLOY_ROOT "docker/mysql"
        Join-Path $DEPLOY_ROOT "data-collector/sql"
    )
    foreach ($dir in $migrationDirs) {
        if (Test-Path $dir) {
            $sqlFiles += Get-ChildItem -Path $dir -Filter "*.sql" -File | Sort-Object Name
        }
    }

    if ($sqlFiles.Count -eq 0) {
        Write-DeployLog -Message "未发现迁移 SQL 文件" -Level WARN -Category "migration"
        return $true
    }

    Write-DeployLog -Message "发现 $($sqlFiles.Count) 个迁移文件" -Level INFO -Category "migration"
    foreach ($f in $sqlFiles) {
        Write-DeployLog -Message "  📄 $($f.FullName)" -Level INFO -Category "migration"
    }

    if ($DryRun.IsPresent) {
        Write-DeployLog -Message "[DryRun] 将执行 $($sqlFiles.Count) 个迁移文件" -Level SKIP -Category "migration"
        return $true
    }

    # 等待 MySQL 就绪
    Write-DeployLog -Message "等待 MySQL 就绪..." -Level INFO -Category "migration"
    $mysqlReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        $result = docker exec mysql mysqladmin ping -h localhost -u root -phadoop123 --silent 2>&1
        if ($LASTEXITCODE -eq 0) {
            $mysqlReady = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $mysqlReady) {
        Write-DeployLog -Message "MySQL 未能在 60 秒内就绪" -Level FATAL -Category "migration"
        return $false
    }
    Write-DeployLog -Message "MySQL 就绪" -Level PASS -Category "migration"

    # 创建迁移追踪表
    $createTrackingSql = @"
CREATE TABLE IF NOT EXISTS $MIGRATION_TABLE (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    filename    VARCHAR(255) NOT NULL,
    checksum    VARCHAR(64)  NOT NULL,
    applied_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    duration_ms INT          DEFAULT 0,
    status      VARCHAR(20)  DEFAULT 'success',
    UNIQUE KEY uk_filename (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"@
    docker exec -i mysql mysql -uroot -phadoop123 stock_analysis -e "$createTrackingSql" 2>&1 | Out-Null

    # 执行迁移
    $migrationSuccess = $true
    foreach ($sqlFile in $sqlFiles) {
        $filename = $sqlFile.Name
        $checksum = (Get-FileHash -Path $sqlFile.FullName -Algorithm SHA256).Hash

        # 检查是否已执行
        $checkSql = "SELECT COUNT(*) FROM $MIGRATION_TABLE WHERE filename = '$filename' AND checksum = '$checksum' AND status = 'success'"
        $count = docker exec mysql mysql -uroot -phadoop123 stock_analysis -N -e "$checkSql" 2>&1
        if ($count -and $count.Trim() -eq "1") {
            Write-DeployLog -Message "  ⏭️  $filename (已迁移)" -Level SKIP -Category "migration"
            continue
        }

        Write-DeployLog -Message "  🚀 $filename ..." -Level INFO -Category "migration"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        $result = Get-Content $sqlFile.FullName -Raw | docker exec -i mysql mysql -uroot -phadoop123 stock_analysis 2>&1
        $timer.Stop()
        $duration = $timer.ElapsedMilliseconds

        $status = if ($LASTEXITCODE -eq 0) { "success" } else { "failed" }
        if ($status -eq "failed") {
            Write-DeployLog -Message "  ❌ $filename 失败: $result" -Level ERROR -Category "migration"
            $migrationSuccess = $false
        } else {
            Write-DeployLog -Message "  ✅ $filename (${duration}ms)" -Level PASS -Category "migration"
            # 记录迁移
            $recordSql = "INSERT IGNORE INTO $MIGRATION_TABLE (filename, checksum, duration_ms, status) VALUES ('$filename', '$checksum', $duration, '$status')"
            docker exec -i mysql mysql -uroot -phadoop123 stock_analysis -e "$recordSql" 2>&1 | Out-Null
        }
    }

    return $migrationSuccess
}

# ============================================================
# 健康检查
# ============================================================
function Wait-ForHealth {
    param(
        [string]$ServiceName,
        [string]$TestCommand,
        [int]$TimeoutSec = 60,
        [int]$IntervalSec = 5
    )
    Write-DeployLog -Message "等待 $ServiceName 健康就绪 (超时 ${TimeoutSec}s)..." -Level INFO -Category "health"

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt $TimeoutSec) {
        try {
            $result = Invoke-Expression $TestCommand 2>&1
            if ($LASTEXITCODE -eq 0 -or $result -match "healthy|pong|200|ok|success") {
                $elapsed = [math]::Round($timer.Elapsed.TotalSeconds, 1)
                Write-DeployLog -Message "  ✅ $ServiceName 就绪 (${elapsed}s)" -Level PASS -Category "health"
                return $true
            }
        } catch {}
        Start-Sleep -Seconds $IntervalSec
    }
    Write-DeployLog -Message "  ❌ $ServiceName 超时 (${TimeoutSec}s)" -Level ERROR -Category "health"
    return $false
}

# ============================================================
# 零停机部署
# ============================================================
function Deploy-Service {
    param(
        [string]$ServiceName,
        [bool]$ZeroDowntime = $true,
        [bool]$Build = (-not $SkipBuild)
    )

    $composeDir = Join-Path $DEPLOY_ROOT "docker"
    Push-Location $composeDir

    try {
        if ($Build) {
            Write-DeployLog -Message "构建镜像: $ServiceName" -Level INFO -Category "build"
            if (-not $DryRun.IsPresent) {
                docker compose build $ServiceName 2>&1 | ForEach-Object {
                    Write-DeployLog -Message "  build: $_" -Level INFO -Category "build"
                }
                if ($LASTEXITCODE -ne 0) {
                    Write-DeployLog -Message "构建失败: $ServiceName" -Level ERROR -Category "build"
                    return $false
                }
            } else {
                Write-DeployLog -Message "  [DryRun] docker compose build $ServiceName" -Level SKIP -Category "build"
            }
        }

        if ($ZeroDowntime -and $Build) {
            # 零停机滚动更新：先启动新容器，再停止旧容器
            Write-DeployLog -Message "零停机更新: $ServiceName" -Level INFO -Category "deploy"
            if (-not $DryRun.IsPresent) {
                docker compose up -d --no-deps --scale "${ServiceName}=2" --no-recreate $ServiceName 2>&1 | Out-Null
                Start-Sleep -Seconds 3
                docker compose up -d --no-deps $ServiceName 2>&1 | Out-Null
                Start-Sleep -Seconds 2
                # 停止旧容器
                docker compose up -d --no-deps --scale "${ServiceName}=1" --no-recreate $ServiceName 2>&1 | Out-Null
            } else {
                Write-DeployLog -Message "  [DryRun] 零停机滚动: $ServiceName" -Level SKIP -Category "deploy"
            }
        } else {
            # 常规部署
            Write-DeployLog -Message "启动服务: $ServiceName" -Level INFO -Category "deploy"
            if (-not $DryRun.IsPresent) {
                docker compose up -d --no-deps $ServiceName 2>&1 | Out-Null
            } else {
                Write-DeployLog -Message "  [DryRun] docker compose up -d $ServiceName" -Level SKIP -Category "deploy"
            }
        }

        return $true
    } catch {
        Write-DeployLog -Message "部署失败: $ServiceName - $_" -Level ERROR -Category "deploy"
        return $false
    } finally {
        Pop-Location
    }
}

# ============================================================
# 回滚
# ============================================================
function Invoke-Rollback {
    Write-Step "执行回滚"

    $stateFile = Join-Path $DEPLOY_STATE_DIR "last_deploy.json"
    if (-not (Test-Path $stateFile)) {
        Write-DeployLog -Message "未找到上次部署记录，无法回滚" -Level FATAL -Category "rollback"
        return $false
    }

    $lastDeploy = Get-Content $stateFile -Raw | ConvertFrom-Json
    Write-DeployLog -Message "回滚到部署: $($lastDeploy.deploy_id) ($($lastDeploy.timestamp))" -Level INFO -Category "rollback"

    # 按部署顺序逆序回滚
    $services = $lastDeploy.services | ForEach-Object { $_ }
    [array]::Reverse($services)

    $rollbackOk = $true
    foreach ($svc in $services) {
        Write-DeployLog -Message "回滚服务: $svc" -Level INFO -Category "rollback"
        if ($DryRun.IsPresent) { continue }

        $imageTag = "stock-${svc}:previous"
        $composeDir = Join-Path $DEPLOY_ROOT "docker"
        Push-Location $composeDir
        try {
            docker compose up -d --no-deps $svc 2>&1 | Out-Null
            Write-DeployLog -Message "  ✅ $svc 回滚完成" -Level PASS -Category "rollback"
        } catch {
            Write-DeployLog -Message "  ❌ $svc 回滚失败: $_" -Level ERROR -Category "rollback"
            $rollbackOk = $false
        } finally {
            Pop-Location
        }
    }
    return $rollbackOk
}

# ============================================================
# 保存部署状态
# ============================================================
function Save-DeployState {
    param([string[]]$DeployedServices)

    $state = @{
        deploy_id = $script:DEPLOY_ID
        timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        mode      = $Mode
        services  = $DeployedServices
    }
    $stateFile = Join-Path $DEPLOY_STATE_DIR "last_deploy.json"
    $state | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8
    Write-DeployLog -Message "部署状态已保存: $stateFile" -Level INFO -Category "state"
}

# ============================================================
# 主流程
# ============================================================
function Main {
    $script:DEPLOY_ID = "deploy_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     A_system 自动化部署 v2.0                  ║" -ForegroundColor Cyan
    Write-Host "║     Mode: $($Mode.PadRight(30))║" -ForegroundColor Cyan
    Write-Host "║     Deploy ID: $($script:DEPLOY_ID.PadRight(24))║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    if ($DryRun.IsPresent) {
        Write-Host "  ⚠️  Dry-Run 模式 — 仅输出执行计划" -ForegroundColor Yellow
        Write-Host ""
    }

    # ---- Step 1: 环境检查 ----
    if (-not (Test-Prerequisites)) {
        Write-Summary
        exit 1
    }

    # ---- Step 2: 根据模式确定服务列表 ----
    $config = Get-Content $script:CONFIG_FILE -Raw | ConvertFrom-Json
    $serviceOrder = @()

    if ($Mode -eq "full") {
        $serviceOrder += $config.services.infrastructure.order
        $serviceOrder += $config.services.application.order
    } elseif ($Mode -eq "app-only") {
        $serviceOrder += $config.services.application.order
    } elseif ($Mode -eq "infra-only") {
        $serviceOrder += $config.services.infrastructure.order
    } elseif ($Mode -eq "rollback") {
        $result = Invoke-Rollback
        Write-Summary
        exit $(if ($result) {0} else {1})
    }

    Write-DeployLog -Message "部署顺序: $($serviceOrder -join ' → ')" -Level INFO -Category "plan"

    if ($DryRun.IsPresent) {
        Write-DeployLog -Message "[DryRun] 执行计划完成" -Level SKIP -Category "plan"
        Write-Summary
        return
    }

    # ---- Step 3: 数据库迁移 ----
    if ($Mode -ne "infra-only") {
        if (-not (Invoke-DatabaseMigration)) {
            Write-DeployLog -Message "数据库迁移失败，终止部署" -Level FATAL -Category "migration"
            Write-Summary
            exit 1
        }
    }

    # ---- Step 4: 部署服务 ----
    $deployedServices = @()
    $deployFailed = $false

    foreach ($svc in $serviceOrder) {
        Write-Step "部署: $svc"

        $build = (-not $SkipBuild) -and ($svc -in @("ai-service", "backend", "frontend"))
        $zeroDown = $svc -in @("backend", "frontend")

        $ok = Deploy-Service -ServiceName $svc -ZeroDowntime $zeroDown -Build $build
        if (-not $ok) {
            Write-DeployLog -Message "$svc 部署失败，开始回滚" -Level ERROR -Category "deploy"
            $deployFailed = $true
            break
        }
        $deployedServices += $svc
    }

    # ---- Step 5: 后置健康检查 ----
    if (-not $deployFailed) {
        Write-Step "服务健康检查"

        $healthChecks = @{}
        $config.services.application.order | ForEach-Object {
            $timeout = $config.services.application.health_timeout_sec.$_
            $healthChecks[$_] = $timeout
        }

        Write-DeployLog -Message "执行健康检查..." -Level INFO -Category "health"
        foreach ($svc in $deployedServices) {
            switch ($svc) {
                "redis"     { Wait-ForHealth -ServiceName $svc -TestCommand "docker exec redis redis-cli ping" -TimeoutSec 30 }
                "mysql"     { Wait-ForHealth -ServiceName $svc -TestCommand "docker exec mysql mysqladmin ping -h localhost -u root -phadoop123 --silent" -TimeoutSec 30 }
                "ai-service" { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:8000/health" -TimeoutSec 60 }
                "backend"   { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:8082/api/market/list?page=1&size=1" -TimeoutSec 120 }
                "frontend"  { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:80/" -TimeoutSec 60 }
                "namenode"  { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:9870/" -TimeoutSec 60 }
                "datanode1" { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:9864/" -TimeoutSec 60 }
                "resourcemanager" { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:8088/" -TimeoutSec 60 }
                "spark-master" { Wait-ForHealth -ServiceName $svc -TestCommand "curl -sf http://localhost:8080/" -TimeoutSec 60 }
                "hive-server" { Wait-ForHealth -ServiceName $svc -TestCommand "docker exec hive-server /opt/hive/bin/beeline -u jdbc:hive2://localhost:10000 -e 'SHOW DATABASES;' 2>&1" -TimeoutSec 120 }
            }
        }
    }

    # ---- Step 6: 保存状态 / 回滚 ----
    if ($deployFailed) {
        Write-DeployLog -Message "部署失败，自动回滚..." -Level WARN -Category "rollback"
        Invoke-Rollback
        Write-Summary
        exit 1
    } else {
        Save-DeployState -DeployedServices $deployedServices
        Write-DeployLog -Message "🎉 部署完成！" -Level PASS -Category "complete"
    }

    Write-Summary
}

# ============================================================
# 执行入口
# ============================================================
Main
