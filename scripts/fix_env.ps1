<#
.SYNOPSIS
    环境修复脚本 — 修复诊断出的问题，不破坏现有项目依赖和运行服务
#>

$OutputEncoding = [System.Text.Encoding]::UTF8
$FIX_LOG = "f:/bs/A_system/logs/env_fix_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$fixes = @()

function fix($msg) { $fixes += $msg; "$(Get-Date -Format 'HH:mm:ss') [FIX] $msg" | Out-File -FilePath $FIX_LOG -Encoding UTF8 -Append; Write-Host "🔧 $msg" }
function skip($msg) { "$(Get-Date -Format 'HH:mm:ss') [SKIP] $msg" | Out-File -FilePath $FIX_LOG -Encoding UTF8 -Append; Write-Host "⏭️  $msg" }
function ok($msg) { "$(Get-Date -Format 'HH:mm:ss') [OK] $msg" | Out-File -FilePath $FIX_LOG -Encoding UTF8 -Append; Write-Host "✅ $msg" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  环境修复脚本 — 自动修复" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ====== 1. 检查 Java/Maven 实际可用性 ======
Write-Host "`n[1/4] 验证 Java/Maven" -ForegroundColor Yellow
try {
    $jv = java -version 2>&1
    if ($jv -match "java version|openjdk version") { ok "Java: $($jv[0].Trim())" }
    else { fix "Java 命令可用但版本检测异常" }
} catch { fix "Java 不可用 — 请检查 JAVA_HOME=$env:JAVA_HOME 是否有效" }

try {
    $mv = mvn --version 2>&1 | Select-String "Apache Maven"
    if ($mv) { ok "Maven: $($mv.ToString().Trim())" }
} catch { fix "Maven 不可用" }

# ====== 2. 恢复端口服务 ======
Write-Host "`n[2/4] 恢复端口服务" -ForegroundColor Yellow

# 前端 :5173
$port5173 = netstat -ano | Select-String ":5173 " | Select-String "LISTENING"
if (-not $port5173) {
    fix "前端端口 5173 空闲 — 重启 Vite 开发服务器"
    try {
        # 检查有没有残留的 node 进程
        Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "vite" } | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Process powershell -ArgumentList "-NoExit -Command cd f:\bs\A_system\frontend; Write-Host 'Vite Dev Server starting...'; npm run dev" -WindowStyle Normal
        Start-Sleep -Seconds 4
        $r = curl.exe -s -o nul -w "%{http_code}" "http://localhost:5173" 2>$null
        if ($r -eq 200) { ok "前端已启动 (HTTP 200)" } else { fix "前端启动后返回 HTTP $r，请手动检查" }
    } catch { fix "前端启动失败: $_" }
} else { ok "前端端口 5173 已在监听" }

# AI 服务 :8000 — 验证内容而非 HTTP 状态码
try {
    $aiBody = curl.exe -s "http://localhost:8000/health" 2>$null
    if ($aiBody -match '"status":"ok"') { ok "AI 服务健康 — 返回: $aiBody" }
    else { fix "AI 服务返回异常: $aiBody" }
} catch { fix "AI 服务不可达" }

# ====== 3. Docker 不健康容器 ======
Write-Host "`n[3/4] 检查 Docker 不健康容器" -ForegroundColor Yellow
try {
    $unhealthy = docker ps --filter "health=unhealthy" --format "{{.Names}}" 2>$null
    if ($unhealthy) {
        foreach ($c in $unhealthy) {
            if ($c -eq "hive-server") {
                skip "hive-server — Hive 2.3.2 启动慢属正常现象，非核心服务不影响开发"
            } elseif ($c -eq "data-collector") {
                skip "data-collector — Python 代码级问题(KlineCollector 参数)，需修复代码"
            } else {
                fix "重启不健康容器: $c"
                docker restart $c 2>$null
            }
        }
    } else { ok "所有容器健康（或未设置 healthcheck）" }
} catch { skip "Docker 不可用，跳过" }

# ====== 4. 环境变量建议 ======
Write-Host "`n[4/4] 环境变量建议" -ForegroundColor Yellow
$suggestions = @()
if (-not [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY","User") -and -not [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY","Machine")) {
    $suggestions += "DEEPSEEK_API_KEY — AI 真实对话功能需要，缺失时自动降级为模拟模式"
}
if ($suggestions.Count -gt 0) {
    skip "以下环境变量建议设置（非必须）:"
    foreach ($s in $suggestions) { skip "  - $s" }
} else { ok "环境变量配置完整" }

# ====== 汇总 ======
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  修复完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  📋 修复日志: $FIX_LOG" -ForegroundColor Cyan
Write-Host "  🔧 执行修复: $($fixes.Count) 项" -ForegroundColor Cyan
if ($fixes.Count -eq 0) { Write-Host "  ✅ 环境已就绪，无需修复" -ForegroundColor Green }
else { foreach ($f in $fixes) { Write-Host "     - $f" } }
Write-Host "========================================" -ForegroundColor Cyan
