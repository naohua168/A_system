# 记录本次开发会话的开始时间（供 end-of-day.ps1 计算运行时长）
[long](Get-Date -UFormat %s) | Out-File (Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) ".session_start") -Encoding UTF8
Write-Host "✅ 开发会话已开始" -ForegroundColor Green