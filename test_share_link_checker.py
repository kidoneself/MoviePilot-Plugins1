#!/usr/bin/env python3
"""
分享链接检查器测试脚本
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8080"

def test_check_missing_links():
    """测试检查缺失链接"""
    print("=" * 60)
    print("测试1: 检查缺失链接（不发送通知）")
    print("=" * 60)
    
    try:
        url = f"{BASE_URL}/api/check-missing-links?send_notification=false"
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 检查成功!")
            print(f"\n检查时间: {result.get('check_time')}")
            print(f"资源总数: {result.get('total_mappings')}个")
            
            missing_counts = result.get('missing_counts', {})
            print(f"\n缺失统计:")
            print(f"  百度网盘: {missing_counts.get('baidu', 0)}个")
            print(f"  夸克网盘: {missing_counts.get('quark', 0)}个")
            print(f"  迅雷网盘: {missing_counts.get('xunlei', 0)}个")
            print(f"  全部缺失: {missing_counts.get('all_missing', 0)}个")
            
            return True
        else:
            print(f"❌ 检查失败: HTTP {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def test_get_missing_links(pan_type='all'):
    """测试获取缺失链接列表"""
    print("\n" + "=" * 60)
    print(f"测试2: 获取{pan_type}网盘缺失链接")
    print("=" * 60)
    
    try:
        url = f"{BASE_URL}/api/missing-links/{pan_type}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 查询成功!")
            print(f"\n网盘类型: {result.get('pan_type')}")
            print(f"缺失总数: {result.get('total_count')}个")
            
            categories = result.get('categories', {})
            print(f"\n分类统计:")
            for category, items in categories.items():
                print(f"  {category}: {len(items)}个")
                # 显示前3个
                for i, item in enumerate(items[:3], 1):
                    completed = "✅" if item.get('is_completed') else "🔄"
                    print(f"    {i}. {completed} {item.get('original_name')}")
                
                if len(items) > 3:
                    print(f"    ... 还有{len(items) - 3}个")
            
            return True
        else:
            print(f"❌ 查询失败: HTTP {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def test_health_check():
    """测试服务健康检查"""
    print("=" * 60)
    print("测试0: 服务健康检查")
    print("=" * 60)
    
    try:
        url = f"{BASE_URL}/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 服务运行正常: {result}")
            return True
        else:
            print(f"❌ 服务异常: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        print(f"\n请确保服务已启动: python -m backend.main")
        return False


def main():
    """主测试流程"""
    print("\n🧪 分享链接检查器功能测试")
    print("=" * 60)
    
    # 1. 健康检查
    if not test_health_check():
        print("\n❌ 服务未启动，退出测试")
        sys.exit(1)
    
    # 2. 检查缺失链接
    if not test_check_missing_links():
        print("\n⚠️ 检查缺失链接失败")
    
    # 3. 查询各网盘缺失链接
    for pan_type in ['all', 'baidu', 'quark', 'xunlei']:
        if not test_get_missing_links(pan_type):
            print(f"\n⚠️ 查询{pan_type}缺失链接失败")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    
    print("\n💡 提示:")
    print("1. 如果所有测试通过，说明检查器工作正常")
    print("2. 可以修改 send_notification=true 来测试微信通知")
    print("3. 建议在生产环境设置定时任务自动检查")
    print("\n详细使用指南: docs/SHARE_LINK_CHECKER_GUIDE.md")


if __name__ == '__main__':
    main()

