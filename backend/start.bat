@echo off
chcp 65001 >nul

REM 检查 .env 文件是否存在
if not exist .env (
    echo [错误] 找不到 .env 文件！
    echo 请复制 .env.example 为 .env 并填写您的配置
    echo.
    echo 命令: copy .env.example .env
    pause
    exit /b 1
)

echo [启动] 正在启动后端服务...
echo [提示] 配置将从 .env 文件加载

.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo [错误] 启动失败！
    pause
)
