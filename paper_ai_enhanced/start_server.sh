#!/bin/bash
# 启动后端API服务器

cd "$(dirname "$0")"

echo "启动Paper AI API服务器..."

# 激活虚拟环境
source venv/bin/activate

# 启动服务器
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
