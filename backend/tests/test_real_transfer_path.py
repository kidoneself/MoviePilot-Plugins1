#!/usr/bin/env python3
"""
模拟真实转存路径检查过程
测试为什么会重复创建文件夹
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import requests


def simulate_path_check(user_path: str, pan_type: str):
    """
    模拟 UnifiedTransfer.get_transfer_param 的逻辑
    看看到底哪一层会出问题
    """
    
    print("=" * 80)
    print(f"模拟路径检查: {pan_type} - {user_path}")
    print("=" * 80)
    
    OPENLIST_URL = "http://10.10.10.17:5255"
    OPENLIST_TOKEN = "openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4"
    
    PAN_MOUNT_MAP = {
        'baidu': 'baidu',
        'quark': 'kuake',
        'xunlei': 'xunlei'
    }
    
    headers = {
        'Authorization': OPENLIST_TOKEN,
        'Content-Type': 'application/json'
    }
    
    mount_point = PAN_MOUNT_MAP.get(pan_type)
    if not mount_point:
        print(f"❌ 不支持的网盘类型: {pan_type}")
        return
    
    # 构建完整路径
    full_path = f"/{mount_point}{user_path}"
    print(f"\n完整路径: {full_path}")
    
    # 分解路径
    parts = [p for p in full_path.split('/') if p]
    print(f"路径层级: {parts}")
    print(f"共 {len(parts)} 层")
    
    current_path = ""
    
    # 逐层检查
    for idx, part in enumerate(parts, 1):
        current_path = f"{current_path}/{part}"
        parent_path = "/".join(current_path.split('/')[:-1]) or "/"
        
        print(f"\n{'='*80}")
        print(f"第 {idx}/{len(parts)} 层")
        print(f"当前层名称: '{part}'")
        print(f"父目录路径: {parent_path}")
        print(f"当前完整路径: {current_path}")
        print('-'*80)
        
        # 列出父目录
        try:
            response = requests.post(
                f"{OPENLIST_URL}/api/fs/list",
                json={"path": parent_path, "page": 1, "per_page": 1000, "refresh": False},
                headers=headers,
                timeout=10
            )
            result = response.json()
            
            if result.get('code') != 200:
                print(f"❌ 列出父目录失败: {result.get('message')}")
                continue
            
            content = result.get('data', {}).get('content', [])
            print(f"父目录包含 {len(content)} 项")
            
            # 记录所有文件夹
            folders = [item for item in content if item.get('is_dir') or item.get('mount_details')]
            print(f"\n父目录下的文件夹/挂载点 ({len(folders)} 个):")
            for item in folders[:10]:  # 只显示前10个
                name = item.get('name', '')
                is_dir = item.get('is_dir')
                is_mount = item.get('mount_details') is not None
                item_id = item.get('id', 'N/A')
                print(f"  - {name:40s} | is_dir: {str(is_dir):5s} | is_mount: {str(is_mount):5s}")
            
            if len(folders) > 10:
                print(f"  ... 还有 {len(folders) - 10} 个")
            
            # 查找匹配
            print(f"\n🔍 查找目标: '{part}'")
            found = False
            matched_item = None
            
            for item in content:
                # 新逻辑：检查挂载点或目录
                is_mount = item.get('mount_details') is not None
                is_directory = item.get('is_dir') == True
                item_name = item.get('name', '')
                
                # 标准化比对
                item_name_clean = item_name.strip() if item_name else ''
                part_clean = part.strip()
                
                # 匹配条件
                if item_name_clean == part_clean and (is_directory or is_mount):
                    folder_id = item.get('id', '')
                    found = True
                    matched_item = item
                    print(f"✅ 找到匹配:")
                    print(f"   名称: '{item_name}'")
                    print(f"   is_dir: {is_directory}")
                    print(f"   is_mount: {is_mount}")
                    print(f"   ID: {folder_id}")
                    break
            
            if not found:
                print(f"❌ 未找到匹配")
                print(f"\n详细对比（前10项）:")
                for i, item in enumerate(content[:10]):
                    item_name = item.get('name', '')
                    is_dir = item.get('is_dir')
                    is_mount = item.get('mount_details') is not None
                    
                    # 比较
                    exact_match = item_name == part
                    strip_match = item_name.strip() == part.strip()
                    
                    if exact_match or strip_match or part in item_name:
                        print(f"  [{i+1}] '{item_name}'")
                        print(f"      exact_match: {exact_match}")
                        print(f"      strip_match: {strip_match}")
                        print(f"      is_dir: {is_dir}, is_mount: {is_mount}")
                        print(f"      repr: {repr(item_name)} vs {repr(part)}")
                
                print(f"\n⚠️  将尝试创建: {current_path}")
            
        except Exception as e:
            print(f"❌ 检查失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("检查完成")
    print('='*80)


if __name__ == '__main__':
    # 测试用户实际使用的路径
    test_cases = [
        ("/A-闲鱼影视（自动更新）/电影", "baidu"),
        ("/A-闲鱼影视（自动更新）/剧集/国产剧集", "baidu"),
        ("/A-闲鱼影视（自动更新）/其他/综艺节目", "baidu"),
    ]
    
    for user_path, pan_type in test_cases:
        simulate_path_check(user_path, pan_type)
        print("\n\n")

