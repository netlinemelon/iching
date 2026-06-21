@echo off
chcp 65001 >nul
title 八卦 - I Ching 占卜

cd /d "%~dp0"

:: 如果 .env 存在则加载环境变量，否则提示用户配置
if exist ".env" (
    echo [OK] Found .env, loading configuration...
) else (
    echo [INFO] No .env found, copying from .env.example...
    copy .env.example .env >nul 2>nul
    echo [INFO] Created .env from template. Edit .env to add your API key for AI interpretation.
)

:: 加载 .env 中的变量（简单解析 KEY=VALUE 格式）
for /f "usebackq tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%a"=="#" set "%%a=%%b"
)

:: 安装依赖（首次运行或更新时）
echo [INFO] Installing dependencies...
pip install -r requirements.txt -q 2>nul

:: 启动服务
set PORT=%PORT:-21882%
set HOST=%HOST:-127.0.0.1%

echo.
echo  ╔══════════════════════════════════╗
echo  ║     八卦 I Ching 占卜系统       ║
echo  ║                                 ║
echo  ║  启动中...                      ║
echo  ║  打开浏览器访问                  ║
echo  ║  http://%HOST%:%PORT%           ║
echo  ╚══════════════════════════════════╝
echo.

:: 等一秒后打开浏览器
start "" http://%HOST%:%PORT%

python run.py

pause
