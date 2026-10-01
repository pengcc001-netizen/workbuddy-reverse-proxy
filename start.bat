@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title WorkBuddy Reverse Proxy

echo ========================================
echo   WorkBuddy Reverse Proxy
echo   直连 copilot.tencent.com
echo   端口: 8091
echo ========================================
echo.

cd /d "%~dp0"

REM ---- 检测 Python ----
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo.
    echo   下载地址: https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
    echo.
    echo   或者使用打包版 exe（无需安装 Python）:
    echo   运行 build_exe.bat 生成 workbuddy-proxy.exe
    echo.
    pause
    exit /b 1
)

REM ---- 创建虚拟环境 ----
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 正在创建虚拟环境...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [1/3] 虚拟环境创建完成
    echo.
) else (
    echo [1/3] 虚拟环境已存在
)

REM ---- 安装依赖（仅首次或依赖缺失时）----
echo [2/3] 检查依赖...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, httpx" >nul 2>&1
if !errorlevel! neq 0 (
    echo [2/3] 正在安装依赖（首次运行需等待片刻）...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [错误] 依赖安装失败，请检查网络连接
        echo   可尝试使用国内镜像:
        echo   .venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        pause
        exit /b 1
    )
    echo [2/3] 依赖安装完成
) else (
    echo [2/3] 依赖已就绪
)
echo.

REM ---- 启动服务 ----
echo [3/3] 启动服务...
echo.
".venv\Scripts\python.exe" main.py

echo.
echo 服务已停止
pause
