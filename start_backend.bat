@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [提示] 虚拟环境不存在，尝试使用系统 Python...
)

REM 设置环境变量
set PYTHONIOENCODING=utf-8

REM 启动后端
echo.
echo ========================================
echo 启动 DocuVista 后端服务...
echo ========================================
python backend_run.py
pause
