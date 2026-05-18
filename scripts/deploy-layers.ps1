<#
.SYNOPSIS
双层架构部署脚本 — 独立管理采集层/大数据层

.DESCRIPTION
支持分层启动、停止、状态查看，确保层间隔离和数据流转正确

架构:
  采集层 (collector-net):  zookeeper + kafka + data-collector
  大数据层 (bigdata-net):  HDFS + YARN + Hive + Spark + MySQL + Redis + App

数据流:
  采集层 → Kafka(双网卡) → 大数据层(Spark Streaming)
  采集层 → 共享卷(CSV)  → 大数据层(HDFS批量导入)

.PARAMETER Mode
  up       启动指定层
  down     停止指定层
  restart  重启指定层
  status   查看指定层状态
  logs     查看指定层日志

.PARAMETER Layer
  collector   仅采集层
  bigdata     仅大数据层
  all (默认)   全部层（先采集后大数据）

.EXAMPLE
  .\deploy-layers.ps1 -Mode up -Layer all
  .\deploy-layers.ps1 -Mode up -Layer collector
  .\deploy-layers.ps1 -Mode status -Layer bigdata
  .\deploy-layers.ps1 -Mode logs -Layer collector -Follow
#>

param(
    [ValidateSet("up", "down", "restart", "status", "logs")]
    [string]$Mode = "up",

    [ValidateSet("collector", "bigdata", "all")]
    [string]$Layer = "all",

    [switch]$Follow,
    [switch]$Build,
    [switch]$DryRun
)

$DOCKER_DIR = Join-Path $PSScriptRoot ".." "docker" | Resolve-Path
$COMPOSE_COLLECTOR = Join-Path $DOCKER_DIR "docker-compose.collector.yml"
$COMPOSE_BIGDATA = Join-Path $DOCKER_DIR "docker-compose.yml"
$COMPOSE_PROD = Join-Path $DOCKER_DIR "docker-compose.prod.yml"
$COMPOSE_DEV = Join-Path $DOCKER_DIR "docker-compose.dev.yml"
$COMPOSE_BRIDGE = Join-Path $DOCKER_DIR "docker-compose.bridge.yml"

function Write-Banner {
    param($Title, $Color = "Cyan")
    Write-Host ("`n" + "=" * 55) -ForegroundColor $Color
    Write-Host " $Title" -ForegroundColor $Color
    Write-Host ("=" * 55) -ForegroundColor $Color
}

function Invoke-DockerCompose {
    param(
        [string]$ComposeFile,
        [string]$Mode,
        [string[]]$ExtraFiles = @(),
        [switch]$Build,
        [switch]$Follow,
        [switch]$DryRun
    )

    $files = @("-f", $ComposeFile)
    foreach ($ef in $ExtraFiles) {
        if (Test-Path $ef) { $files += @("-f", $ef) }
    }

    switch ($Mode) {
        "up" {
            $cmd = @("compose") + $files + @("up", "-d")
            if ($Build) { $cmd += "--build" }
        }
        "down" { $cmd = @("compose") + $files + @("down") }
        "restart" { $cmd = @("compose") + $files + @("restart") }
        "status" { $cmd = @("compose") + $files + @("ps") }
        "logs" {
            $cmd = @("compose") + $files + @("logs")
            if ($Follow) { $cmd += "-f" }
        }
    }

    Write-Host "   docker $($cmd -join ' ')" -ForegroundColor Gray
    if (-not $DryRun) {
        & docker $cmd
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ❌ 命令失败 (exit code: $LASTEXITCODE)" -ForegroundColor Red
        }
    } else {
        Write-Host "  [DRY-RUN] 跳过执行" -ForegroundColor Yellow
    }
}

# ============================================================
# 主逻辑
# ============================================================
Write-Banner "📦 双层架构部署工具"

switch ($Mode) {
    "up" {
        if ($Layer -eq "collector" -or $Layer -eq "all") {
            Write-Banner "Layer 1: 数据采集层 (collector-net)" Yellow
            $extraFiles = @()
            if ($Build) { $extraFiles = @() }  # Build handled by flag
            Invoke-DockerCompose -ComposeFile $COMPOSE_COLLECTOR -Mode up -Build:$Build -DryRun:$DryRun
        }

        if ($Layer -eq "bigdata" -or $Layer -eq "all") {
            Write-Banner "Layer 2: 大数据层 (bigdata-net)" Green
            $extraFiles = @($COMPOSE_PROD)
            if (-not (Test-Path $COMPOSE_PROD)) { $extraFiles = @() }
            Invoke-DockerCompose -ComposeFile $COMPOSE_BIGDATA -Mode up `
                -ExtraFiles $extraFiles -Build:$Build -DryRun:$DryRun
        }
    }

    "down" {
        # 大数据层先停（依赖采集层的资源先释放）
        if ($Layer -eq "bigdata" -or $Layer -eq "all") {
            Write-Banner "🛑 停止: 大数据层" Green
            Invoke-DockerCompose -ComposeFile $COMPOSE_BIGDATA -Mode down -DryRun:$DryRun
        }

        if ($Layer -eq "collector" -or $Layer -eq "all") {
            Write-Banner "🛑 停止: 数据采集层" Yellow
            Invoke-DockerCompose -ComposeFile $COMPOSE_COLLECTOR -Mode down -DryRun:$DryRun
        }
    }

    "restart" {
        if ($Layer -eq "collector" -or $Layer -eq "all") {
            Write-Banner "🔄 重启: 数据采集层" Yellow
            Invoke-DockerCompose -ComposeFile $COMPOSE_COLLECTOR -Mode restart -DryRun:$DryRun
        }

        if ($Layer -eq "bigdata" -or $Layer -eq "all") {
            Write-Banner "🔄 重启: 大数据层" Green
            $extraFiles = @($COMPOSE_PROD)
            if (-not (Test-Path $COMPOSE_PROD)) { $extraFiles = @() }
            Invoke-DockerCompose -ComposeFile $COMPOSE_BIGDATA -Mode restart `
                -ExtraFiles $extraFiles -DryRun:$DryRun
        }
    }

    "status" {
        if ($Layer -eq "collector" -or $Layer -eq "all") {
            Write-Banner "📊 数据采集层状态" Yellow
            Invoke-DockerCompose -ComposeFile $COMPOSE_COLLECTOR -Mode status
        }

        if ($Layer -eq "bigdata" -or $Layer -eq "all") {
            Write-Banner "📊 大数据层状态" Green
            Invoke-DockerCompose -ComposeFile $COMPOSE_BIGDATA -Mode status
        }

        # 显示整体概览
        Write-Banner "📋 全部容器运行概览" White
        docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
    }

    "logs" {
        if ($Layer -eq "collector" -or $Layer -eq "all") {
            Write-Banner "📜 采集层日志" Yellow
            Invoke-DockerCompose -ComposeFile $COMPOSE_COLLECTOR -Mode logs -Follow:$Follow
        }

        if ($Layer -eq "bigdata" -or $Layer -eq "all") {
            Write-Banner "📜 大数据层日志" Green
            Invoke-DockerCompose -ComposeFile $COMPOSE_BIGDATA -Mode logs -Follow:$Follow
        }
    }
}

# 如果启动了大数据层，检查容器是否就绪
if ($Mode -eq "up" -and -not $DryRun) {
    if ($Layer -eq "bigdata" -or $Layer -eq "all") {
        Write-Banner "⏳ 等待大数据层就绪..." Cyan
        Write-Host "  可通过以下命令查看状态:"
        Write-Host "    .\deploy-layers.ps1 -Mode status" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  Web UI 地址:"
        Write-Host "    HDFS:        http://localhost:9870" -ForegroundColor Gray
        Write-Host "    YARN:        http://localhost:8088" -ForegroundColor Gray
        Write-Host "    Hive:        http://localhost:10002" -ForegroundColor Gray
        Write-Host "    Spark:       http://localhost:8080" -ForegroundColor Gray
        Write-Host "    ️Frontend:   http://localhost:80" -ForegroundColor Gray
    }

    if ($Layer -eq "collector" -or $Layer -eq "all") {
        Write-Host ""
        Write-Host "  Kafka 地址: collector-kafka:29092 (采集层内部)" -ForegroundColor Yellow
        Write-Host "  Kafka 地址: collector-kafka:39092 (大数据层访问)" -ForegroundColor Yellow
    }
}
