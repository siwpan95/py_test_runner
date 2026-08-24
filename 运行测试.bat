@echo off
chcp 65001 >nul
title 测试框架

cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════════════╗
echo   ║     🧪  测试框架 — 快速启动          ║
echo   ╚══════════════════════════════════════╝
echo.
echo   ── 常规测试 ──
echo   [1] GUI 模式（图形界面）
echo   [2] GUI 模式 — 演示套件（5个测试）
echo   [3] 控制台模式 — 全部测试
echo   [4] 控制台模式 — 演示套件
echo   [5] 控制台模式 — 仅通过测试
echo.
echo   ── 探针测试 ──
echo   [6] 冒烟探针（仅关键路径 P1）
echo   [7] 全部探针
echo   [8] 环境探针
echo   [9] 导入探针
echo.
echo   [0] 退出
echo.
set /p choice="  请选择 [0-9]: "

if "%choice%"=="1" (
    echo  启动 GUI 模式...
    python main.py
) else if "%choice%"=="2" (
    echo  启动 GUI 模式（演示套件）...
    python main.py --demo
) else if "%choice%"=="3" (
    echo  启动控制台模式...
    python main.py --console
) else if "%choice%"=="4" (
    echo  启动控制台模式（演示套件）...
    python main.py --console --demo
) else if "%choice%"=="5" (
    echo  启动控制台模式（仅通过测试）...
    python main.py --console --passing
) else if "%choice%"=="6" (
    echo  冒烟探针扫描中...
    python main.py --console --smoke
) else if "%choice%"=="7" (
    echo  全量探针扫描中...
    python main.py --console --smoke --all
) else if "%choice%"=="8" (
    echo  环境探针扫描中...
    python main.py --console --smoke --category 环境
) else if "%choice%"=="9" (
    echo  导入探针扫描中...
    python main.py --console --smoke --category 导入
) else if "%choice%"=="0" (
    exit /b
) else (
    echo  无效选择！
    pause
)

echo.
echo  测试完成，日志保存在 logs\ 目录下
pause
