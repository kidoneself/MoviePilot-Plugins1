#!/usr/bin/env python3
"""
闲鱼 Playwright 自动化本地测试脚本
用于调试登录和创建卡种流程，无需部署到Docker
"""

import sys
import os
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from backend.utils.xianyu_playwright import KamiAutomation

def step_callback(message: str, status: str):
    """步骤回调函数"""
    emoji_map = {
        'loading': '⏳',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'qrcode': '📱'
    }
    emoji = emoji_map.get(status, '📝')
    
    if status == 'qrcode':
        print(f"\n{emoji} 二维码已获取，请用手机扫码")
        # 可以在这里保存二维码或打开
        if message.startswith('QRCODE:'):
            qr_data = message[7:]  # 去掉 "QRCODE:" 前缀
            print(f"   二维码数据: {qr_data[:100]}...")
    else:
        print(f"{emoji} {message}")


def test_create_kami_kind():
    """测试创建卡种"""
    print("=" * 60)
    print("闲鱼 Playwright 自动化测试")
    print("=" * 60)
    print()
    
    # 使用非无头模式，可以看到浏览器操作
    headless = False
    print(f"🚀 启动浏览器（无头模式: {headless}）")
    
    automation = KamiAutomation(headless=headless)
    automation.set_step_callback(step_callback)
    
    # 测试卡种名称
    import time
    kind_name = "测试卡种_" + str(int(time.time()))
    
    try:
        print(f"\n📦 开始创建卡种: {kind_name}")
        print("-" * 60)
        
        success = automation.create_kami_kind(kind_name)
        
        print("-" * 60)
        if success:
            print(f"✅ 测试成功！卡种 '{kind_name}' 创建完成")
        else:
            print(f"❌ 测试失败！卡种创建失败")
            
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 保持浏览器打开，方便查看
        if not headless:
            input("\n按回车键关闭浏览器...")
        print("\n🔚 测试结束")


def test_add_kami_cards():
    """测试添加卡密"""
    print("=" * 60)
    print("测试添加卡密到卡种")
    print("=" * 60)
    print()
    
    headless = False
    automation = KamiAutomation(headless=headless)
    automation.set_step_callback(step_callback)
    
    kind_name = input("请输入卡种名称: ").strip()
    if not kind_name:
        print("❌ 卡种名称不能为空")
        return False
    
    # 测试卡密数据
    kami_data = """123456 abcdef
789012 ghijkl
345678 mnopqr"""
    
    try:
        print(f"\n📦 开始添加卡密到卡种: {kind_name}")
        print(f"   卡密数量: 3 组")
        print("-" * 60)
        
        success = automation.add_kami_cards(kind_name, kami_data, repeat_count=1)
        
        print("-" * 60)
        if success:
            print(f"✅ 测试成功！卡密已添加到 '{kind_name}'")
        else:
            print(f"❌ 测试失败！卡密添加失败")
            
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if not headless:
            input("\n按回车键关闭浏览器...")
        print("\n🔚 测试结束")


def main():
    """主函数"""
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("\n请选择测试项目：")
        print("1. 测试创建卡种")
        print("2. 测试添加卡密")
        print("3. 退出")
        print("\n或使用命令行参数: python3 test_xianyu_playwright.py [1|2]")
        
        try:
            choice = input("\n请输入选项 (1-3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n使用默认选项: 1 (测试创建卡种)")
            choice = "1"
    
    if choice == "1":
        test_create_kami_kind()
    elif choice == "2":
        test_add_kami_cards()
    elif choice == "3":
        print("👋 再见！")
    else:
        print("❌ 无效选项")
        print("用法: python3 test_xianyu_playwright.py [1|2]")
        print("  1 - 测试创建卡种")
        print("  2 - 测试添加卡密")


if __name__ == "__main__":
    main()

