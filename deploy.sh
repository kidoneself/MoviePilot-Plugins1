#!/bin/bash
# 文件监控硬链接系统 - 一键部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始部署文件监控硬链接系统..."
echo ""

# 解析参数
BUILD_MODE="restart"  # 默认只重启
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_MODE="build"
            shift
            ;;
        --rebuild)
            BUILD_MODE="rebuild"
            shift
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  (无参数)    只重启容器（代码热更新）"
            echo "  --build     重新构建镜像并启动"
            echo "  --rebuild   清除缓存重新构建镜像"
            echo "  --help      显示帮助信息"
            echo ""
            echo "说明:"
            echo "  - 一般代码更新：直接运行 ./deploy.sh"
            echo "  - Dockerfile更新：运行 ./deploy.sh --build"
            echo "  - 依赖或系统包更新：运行 ./deploy.sh --rebuild"
            exit 0
            ;;
        *)
            echo "❌ 未知参数: $1"
            echo "运行 ./deploy.sh --help 查看帮助"
            exit 1
            ;;
    esac
done

echo "📦 部署模式: $BUILD_MODE"
echo ""

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    echo "❌ 错误：当前目录不是Git仓库"
    exit 1
fi

# 检查是否有未提交的更改
if [[ -n $(git status -s) ]]; then
    echo "📝 检测到未提交的更改："
    git status -s
    echo ""
    read -p "是否提交这些更改？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "请输入提交信息: " commit_msg
        git add .
        git commit -m "$commit_msg"
        echo "✅ 代码已提交"
    else
        echo "⚠️  跳过提交，继续部署现有代码"
    fi
fi

# 推送到远程仓库
echo ""
echo "📤 推送代码到远程仓库..."
git push
if [ $? -eq 0 ]; then
    echo "✅ 代码推送成功"
else
    echo "❌ 代码推送失败"
    exit 1
fi

# 检查是否在服务器上运行
echo ""
echo "🔍 检查部署环境..."
if [ -f "/.dockerenv" ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo "✅ 检测到Docker环境，直接重启服务"
    # 如果在容器内，重启当前容器（需要在容器外执行）
    echo "⚠️  请在宿主机上执行: docker restart file-link-monitor"
    exit 0
fi

# 检查Docker是否运行
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker未运行或无权限访问"
    echo "请手动执行: docker restart file-link-monitor"
    exit 1
fi

# 执行部署
case $BUILD_MODE in
    restart)
        echo "🔄 模式：快速重启（代码热更新）"
        echo ""
        
        # 检查容器是否存在
        if docker ps -a --format '{{.Names}}' | grep -q "^file-link-monitor$"; then
            echo "✅ 找到容器: file-link-monitor"
            docker restart file-link-monitor
            
            if [ $? -eq 0 ]; then
                echo "✅ 容器重启成功"
            else
                echo "❌ 容器重启失败"
                exit 1
            fi
        else
            echo "❌ 未找到容器，尝试首次启动..."
            docker-compose up -d
        fi
        ;;
    
    build)
        echo "🏗️  模式：重新构建镜像"
        echo ""
        docker-compose up -d --build
        
        if [ $? -eq 0 ]; then
            echo "✅ 构建并启动成功"
        else
            echo "❌ 构建失败"
            exit 1
        fi
        ;;
    
    rebuild)
        echo "🔨 模式：清除缓存重新构建"
        echo ""
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        
        if [ $? -eq 0 ]; then
            echo "✅ 完全重建成功"
        else
            echo "❌ 重建失败"
            exit 1
        fi
        ;;
esac

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查容器状态
if docker ps --format '{{.Names}}' | grep -q "^file-link-monitor$"; then
    echo "✅ 服务运行正常"
    echo ""
    echo "📱 访问地址："
    echo "   - API文档: http://localhost:9889/docs"
    echo "   - 前端页面: http://localhost:9889"
    echo ""
    echo "📋 查看日志: docker logs -f file-link-monitor"
    
    # 如果是构建模式，验证 Chrome 安装
    if [ "$BUILD_MODE" != "restart" ]; then
        echo ""
        echo "🔍 验证 Chrome 安装..."
        if docker exec file-link-monitor which google-chrome > /dev/null 2>&1; then
            CHROME_VER=$(docker exec file-link-monitor google-chrome --version 2>/dev/null || echo "未知版本")
            DRIVER_VER=$(docker exec file-link-monitor chromedriver --version 2>/dev/null || echo "未安装")
            echo "✅ Chrome: $CHROME_VER"
            echo "✅ ChromeDriver: $DRIVER_VER"
        else
            echo "⚠️  Chrome 未安装（如果不使用闲鱼功能可忽略）"
        fi
    fi
else
    echo "❌ 容器启动失败"
    echo "查看日志: docker logs file-link-monitor"
    exit 1
fi

echo ""
echo "🎉 部署完成！"

