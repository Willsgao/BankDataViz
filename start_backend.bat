@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [错误] 虚拟环境不存在，请先运行 init_env.bat
    pause
    exit /b 1
)

REM 设置环境变量
set PYTHONIOENCODING=utf-8

REM 启动后端
echo.
echo ========================================
echo 启动 DocuVista 后端服务...
echo ========================================
python backend_run.py
