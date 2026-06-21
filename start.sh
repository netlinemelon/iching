#!/bin/bash
# 八卦 - I Ching Divination — Unix/macOS 一键启动
cd "$(dirname "$0")"
pip install -r requirements.txt -q 2>/dev/null
echo "🚀 启动中..."
echo "📖 打开浏览器访问 http://localhost:${PORT:-21882}"
python run.py &
sleep 2
open "http://localhost:${PORT:-21882}" 2>/dev/null || xdg-open "http://localhost:${PORT:-21882}" 2>/dev/null
wait
