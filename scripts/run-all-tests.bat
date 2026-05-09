@echo off
REM ============================================================
REM  基金股票智能分析系统 - 一键测试运行脚本 (Windows)
REM  运行所有模块的测试并输出报告
REM ============================================================

echo ============================================================
echo   StockAI 项目测试套件
echo   运行时间: %DATE% %TIME%
echo ============================================================
echo.

setlocal enabledelayedexpansion
set ROOT=%~dp0..
set EXIT_CODE=0

REM ============================================================
REM 1. 后端测试 (Spring Boot + JUnit 5)
REM ============================================================
echo [1/4] 后端 Spring Boot 测试...
cd /d "%ROOT%\backend"
call mvn test -q 2>nul
if !ERRORLEVEL! EQU 0 (
    echo   [PASS] 后端测试通过
) else (
    echo   [FAIL] 后端测试失败 (错误码: !ERRORLEVEL!)
    set EXIT_CODE=1
)
echo.

REM ============================================================
REM 2. 前端测试 (Vitest)
REM ============================================================
echo [2/4] 前端 Vue3 测试...
cd /d "%ROOT%\frontend"
call npx vitest run 2>nul
if !ERRORLEVEL! EQU 0 (
    echo   [PASS] 前端测试通过
) else (
    echo   [FAIL] 前端测试失败 (错误码: !ERRORLEVEL!)
    set EXIT_CODE=1
)
echo.

REM ============================================================
REM 3. 分析算法测试 (pytest)
REM ============================================================
echo [3/4] 分析算法测试...
cd /d "%ROOT%\analysis-algorithms"
call python -m pytest tests/ -q 2>nul
if !ERRORLEVEL! EQU 0 (
    echo   [PASS] 分析算法测试通过
) else (
    echo   [FAIL] 分析算法测试失败 (错误码: !ERRORLEVEL!)
    set EXIT_CODE=1
)
echo.

REM ============================================================
REM 4. 数据采集测试 (pytest)
REM ============================================================
echo [4/4] 数据采集测试...
cd /d "%ROOT%\data-collector"
call python -m pytest tests/ -q 2>nul
if !ERRORLEVEL! EQU 0 (
    echo   [PASS] 数据采集测试通过
) else (
    echo   [FAIL] 数据采集测试失败 (错误码: !ERRORLEVEL!)
    set EXIT_CODE=1
)
echo.

REM ============================================================
REM 汇总
REM ============================================================
echo ============================================================
if !EXIT_CODE! EQU 0 (
    echo   所有测试通过!
) else (
    echo   部分测试失败，请检查上方日志
)
echo ============================================================

exit /b !EXIT_CODE!
