<#
.SYNOPSIS
    开发环境诊断脚本 — 基金股票智能分析系统
.DESCRIPTION
    自动检测 OS 版本、依赖管理器状态、环境变量、端口占用、Docker 状态、服务健康
#>

$OutputEncoding = [System.Text.Encoding]::UTF8
$LOG = "f:/bs/A_system/logs/env_diagnose_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$issues = @()

function log($msg) { $msg | Out-File -FilePath $LOG -Encoding UTF8 -Append; Write-Host $msg }

log "============================================"
log " 开发环境诊断报告 — $(Get-Date)"
log "============================================"

# ====== 1. OS 版本 ======
log "`n[1/7] 操作系统信息"
$os = Get-CimInstance Win32_OperatingSystem
log "  OS: $($os.Caption) $($os.Version)"
log "  Arch: $($os.OSArchitecture)"
log "  Host: $env:COMPUTERNAME"
log "  User: $env:USERNAME"

# ====== 2. 运行时版本 ======
log "`n[2/7] 运行时版本"
$checks = @(
    @{Name="Node.js"; Cmd="node --version"},
    @{Name="npm"; Cmd="npm --version"},
    @{Name="Python"; Cmd="python --version"},
    @{Name="Java"; Cmd="java -version 2>&1"},
    @{Name="Maven"; Cmd="mvn --version 2>&1 | Select-String 'Apache Maven'"},
    @{Name="Docker"; Cmd="docker --version"},
    @{Name="Docker Compose"; Cmd="docker compose version"}
)
foreach ($c in $checks) {
    try {
        $v = Invoke-Expression $c.Cmd 2>$null
        if ($v) { log "  $($c.Name): $($v.Trim())" } else { log "  ⚠️ $($c.Name): 未找到"; $issues += "缺失: $($c.Name)" }
    } catch { log "  ❌ $($c.Name): 检查失败"; $issues += "不可用: $($c.Name)" }
}

# ====== 3. 依赖包管理器状态 ======
log "`n[3/7] 项目依赖状态"
$deps = @(
    @{Path="f:/bs/A_system/frontend"; Type="前端 (npm)"; Check="node_modules"; Cmd="npm ls --depth=0 2>&1 | Select-String -NotMatch '(deduped|peer dep)' | Select-Object -First 5"}
    @{Path="f:/bs/A_system/ai-service"; Type="AI 服务 (pip)"; Check=""; Cmd="pip list 2>&1 | Select-String 'fastapi|uvicorn|httpx|pydantic'"}
    @{Path="f:/bs/A_system/data-collector"; Type="数据采集 (pip)"; Check=""; Cmd="pip list 2>&1 | Select-String 'pandas|requests|mootdx|akshare'"}
)
foreach ($d in $deps) {
    $pkgOk = $false
    try {
        if ($d.Check -and (Test-Path "$($d.Path)/$($d.Check)")) { $pkgOk = $true }
        $r = Invoke-Expression $d.Cmd 2>$null
        if ($r) { $pkgOk = $true }
    } catch {}
    if ($pkgOk) { log "  ✅ $($d.Type): 依赖已安装" }
    else { log "  ⚠️ $($d.Type): 依赖缺失或部分安装"; $issues += "依赖缺失: $($d.Type)" }
}

# ====== 4. 环境变量 ======
log "`n[4/7] 环境变量"
$envVars = @("JAVA_HOME","M2_HOME","MAVEN_HOME","DEEPSEEK_API_KEY","SILICONFLOW_API_KEY")
foreach ($v in $envVars) {
    $val = [Environment]::GetEnvironmentVariable($v, "User")
    if (-not $val) { $val = [Environment]::GetEnvironmentVariable($v, "Machine") }
    if ($val) { log "  ✅ $v = $($val.Substring(0,[Math]::Min(30,$val.Length)))..." }
    else { log "  ⚠️ $v 未设置" }
}

# ====== 5. 端口占用 ======
log "`n[5/7] 端口占用"
$ports = @(3306, 3307, 5173, 8082, 8000, 6379, 9092, 9870, 8080, 8088, 9090, 3001, 80)
$portData = netstat -ano | Select-String "LISTENING"
foreach ($p in $ports) {
    $match = $portData | Select-String ":$p " | Select-Object -First 1
    if ($match) {
        $procId = $match.ToString().Trim().Split()[-1]
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        log "  :$p → PID $procId ($($proc.ProcessName))"
    } else {
        log "  :$p → 空闲"
        if ($p -in @(5173, 8082, 8000)) { $issues += "服务未运行: 端口 $p 空闲" }
    }
}

# ====== 6. Docker 容器健康 ======
log "`n[6/7] Docker 容器健康"
try {
    $containers = docker ps -a --format "{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}" 2>$null
    $healthy = 0; $unhealthy = 0; $stopped = 0
    foreach ($c in $containers) {
        $parts = $c.Split('|')
        $name = $parts[0]; $status = $parts[1]
        if ($status -match "(healthy|Up)") { $healthy++ }
        elseif ($status -match "unhealthy") { $unhealthy++; $issues += "容器不健康: $name ($status)" }
        else { $stopped++; $issues += "容器已停止: $name ($status)" }
        log "  $name → $status"
    }
    log "  总计: $($containers.Count) 个容器, $healthy 健康, $unhealthy 不健康, $stopped 已停止"
    
    # 检查关键服务连通性
    log "`n[7/7] 关键服务连通性"
    $services = @(
        @{Name="后端 API"; Url="http://localhost:8082/api/user/login"; Method="POST"; Data='{"username":"test","password":"Test1234"}'; Expect="200|400|403|500"}
        @{Name="AI 服务"; Url="http://localhost:8000/health"; Expect="ok"}
        @{Name="前端"; Url="http://localhost:5173"; Expect="200"}
        @{Name="Grafana"; Url="http://localhost:3001"; Expect="200|302"}
    )
    foreach ($s in $services) {
        try {
            if ($s.Method -eq "POST") {
                $r = curl.exe -s -o nul -w "%{http_code}" $s.Url -X POST -H "Content-Type: application/json" -d $s.Data 2>$null
            } else {
                $r = curl.exe -s -o nul -w "%{http_code}" $s.Url 2>$null
            }
            if ($r -match $s.Expect) { log "  ✅ $($s.Name): HTTP $r" }
            else { log "  ❌ $($s.Name): HTTP $r (期望 $($s.Expect))"; $issues += "服务异常: $($s.Name) 返回 $r" }
        } catch { log "  ❌ $($s.Name): 连接失败"; $issues += "服务不可达: $($s.Name)" }
    }
} catch { log "  ⚠️ Docker 未运行"; $issues += "Docker 未运行" }

# ====== 总结 ======
log "`n============================================"
if ($issues.Count -eq 0) {
    log "  ✅ 环境健康，无异常"
} else {
    log "  ⚠️ 发现 $($issues.Count) 个问题:"
    $i = 1; foreach ($issue in $issues | Sort-Object -Unique) { log "    $i. $issue"; $i++ }
}
log "============================================"
log "诊断日志: $LOG"
