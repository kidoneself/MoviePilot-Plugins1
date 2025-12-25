#!/bin/bash

# 文件监控硬链接系统 - 快速启动脚本

echo "🚀 启动文件监控硬链接系统..."
echo ""

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查依赖
if [ ! -d "backend/__pycache__" ]; then
    echo "📦 首次运行，安装依赖..."
    pip3 install -r requirements.txt
fi

# 启动后端
echo "▶️  启动后端服务 (端口 8080)..."
cd "$(dirname "$0")"
# BASE_URL 用于图片上传服务的URL生成，如需外网访问请自行配置
# export BASE_URL=https://your-domain.com
export BASE_URL=http://localhost:8080
python3 -m backend.main &
BACKEND_PID=$!

echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
echo ""
echo "📱 访问地址："
echo "   - 前端首页: http://localhost:8080"
echo "   - 媒体库: http://localhost:8080/media"
echo "   - 自动化工作流: http://localhost:8080/xianyu/auto-workflow"
echo "   - API文档: http://localhost:8080/docs"
echo ""
echo "⏹  停止服务: kill $BACKEND_PID"
echo ""

# 保存PID到文件
echo $BACKEND_PID > .backend.pid

# 等待用户按键
echo "按 Ctrl+C 停止服务"
wait $BACKEND_PID

