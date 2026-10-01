@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Build WorkBuddy Proxy EXE

echo ========================================
echo   WorkBuddy Reverse Proxy - 打包工具
echo   生成独立 exe（其他电脑无需装 Python）
echo ========================================
echo.

cd /d "%~dp0"

REM ---- 检测虚拟环境 ----
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到 .venv 虚拟环境
    echo   请先运行 start.bat 初始化环境
    echo.
    pause
    exit /b 1
)

REM ---- 检测并安装 PyInstaller ----
echo [1/2] 检查 PyInstaller...
".venv\Scripts\python.exe" -c "import PyInstaller" >nul 2>&1
if !errorlevel! neq 0 (
    echo [1/2] 安装 PyInstaller...
    ".venv\Scripts\python.exe" -m pip install pyinstaller
    if !errorlevel! neq 0 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
) else (
    echo [1/2] PyInstaller 已安装
)
echo.

REM ---- 清理旧文件 ----
if exist "dist\workbuddy-proxy.exe" del /q "dist\workbuddy-proxy.exe"
if exist "build\workbuddy-proxy" rmdir /s /q "build\workbuddy-proxy"

REM ---- 打包 ----
echo [2/2] 正在打包（可能需要几分钟，请耐心等待）...
".venv\Scripts\python.exe" -m PyInstaller ^
    --onefile ^
    --name workbuddy-proxy ^
    --collect-all uvicorn ^
    --collect-all fastapi ^
    --collect-all starlette ^
    --collect-all pydantic ^
    --collect-all pydantic_core ^
    --collect-all httpx ^
    --collect-all h11 ^
    --collect-all anyio ^
    main.py

if !errorlevel! neq 0 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成!
echo ========================================
echo.
echo   exe 位置: dist\workbuddy-proxy.exe
echo.
echo   使用方法:
echo   1. 将 dist\workbuddy-proxy.exe 复制到其他电脑
echo   2. 双击运行即可（无需安装 Python）
echo   3. 确保 WorkBuddy 桌面版已安装并登录
echo.
pause
