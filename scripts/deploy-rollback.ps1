<#
.SYNOPSIS
    A_system 部署回滚脚本 — 恢复到上一个稳定版本

.DESCRIPTION
    读取 .deploy/last_deploy.json 状态文件，逆序回滚所有服务。

.PARAMETER TargetDeployId
    指定回滚到某次部署 ID（默认回滚到上一次）

.PARAMETER Service
    仅回滚单个服务

.EXAMPLE
    .\scripts\deploy-rollback.ps1                          # 回滚全部
    .\scripts\deploy-rollback.ps1 -Service backend         # 仅回滚后端
    .\scripts\deploy-rollback.ps1 -TargetDeployId deploy_20260516_120000
#>

param(
    [string]$TargetDeployId,
    [string]$Service
)

$ErrorActionPreference = "Stop"
$DEPLOY_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$STATE_DIR = Join-Path $DEPLOY_ROOT ".deploy"
$BACKUP_DIR = Join-Path $STATE_DIR "backups"
$HISTORY_FILE = Join-Path $STATE_DIR "deploy_history.json"

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║     A_system 回滚工具                         ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Yellow

# 加载部署历史
if (-not (Test-Path $HISTORY_FILE)) {
    Write-Host "❌ 未找到部署历史文件: $HISTORY_FILE" -ForegroundColor Red
    exit 1
}
$history = Get-Content $HISTORY_FILE -Raw | ConvertFrom-Json

if ($TargetDeployId) {
    $target = $history | Where-Object { $_.deploy_id -eq $TargetDeployId }
    if (-not $target) {
        Write-Host "❌ 未找到部署记录: $TargetDeployId" -ForegroundColor Red
        exit 1
    }
} else {
    $target = $history[-2]  # 倒数第二个是上一个版本
    if (-not $target) {
        Write-Host "❌ 无历史版本可回滚" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🎯 目标部署: $($target.deploy_id) ($($target.timestamp))" -ForegroundColor Cyan

$services = @($target.services)
if ($Service) {
    $services = @($Service)
    Write-Host "🎯 仅回滚: $Service" -ForegroundColor Cyan
}

[array]::Reverse($services)

$errors = 0
$composeDir = Join-Path $DEPLOY_ROOT "docker"
Push-Location $composeDir
try {
    foreach ($svc in $services) {
        Write-Host "`n⏪ 回滚: $svc ..." -ForegroundColor Yellow

        # 回退到上一个镜像标签
        $result = docker compose up -d --no-deps $svc 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $svc 回滚完成" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $svc 回滚失败: $result" -ForegroundColor Red
            $errors++
        }
    }
} finally {
    Pop-Location
}

Write-Host "`n═══════════════════════════════════════════════" -ForegroundColor Yellow
if ($errors -eq 0) {
    Write-Host " ✅ 回滚完成" -ForegroundColor Green
} else {
    Write-Host " ⚠️  部分回滚失败 ($errors 个错误)" -ForegroundColor Red
}
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Yellow
exit $errors
