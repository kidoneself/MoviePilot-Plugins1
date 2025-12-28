#!/bin/bash

echo "================================================================"
echo "  夸克智能转存 - 交互式测试"
echo "================================================================"
echo ""
echo "📋 测试配置:"
echo "   分享链接: https://pan.quark.cn/s/a68845606eba#/list/share/336d2f3a165142a9ae1539b2a29f11bf"
echo "   目标路径: /A-闲鱼影视（自动更新）/测试/夸克智能转存测试"
echo ""
echo "⚠️  请在 macOS 终端直接运行此脚本（不要在沙箱环境中运行）"
echo ""
read -p "按 Enter 继续..."

cd /Users/lizhiqiang/coding-my/file-link-monitor/backend
python3 tests/test_quark_smart_transfer.py

