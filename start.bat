@echo off
chcp 65001 >nul
title 八卦 - I Ching 占卜

cd /d "%~dp0"

:: 设置 DeepSeek API Key（如果不设置则使用规则回退）
set ANTHROPIC_API_KEY=REDACTED_API_KEY_PLACEHOLDER

:: 安装依赖（首次运行或更新时）
pip install -r requirements.txt -q 2>nul

:: 启动服务
echo.
echo  ╔══════════════════════════════════╗
echo  ║     八卦 I Ching 占卜系统       ║
echo  ║                                 ║
echo  ║  启动中...                      ║
echo  ║  打开浏览器访问                  ║
echo  ║  http://localhost:8088           ║
echo  ╚══════════════════════════════════╝
echo.

:: 等一秒然后打开浏览器
start "" http://localhost:8088

python -m uvicorn app.main:app --host 127.0.0.1 --port 8088

pause
