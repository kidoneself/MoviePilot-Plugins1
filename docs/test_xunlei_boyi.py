#!/usr/bin/env python3
"""
测试通过 mapping 表查找"搏忆"并获取文件信息
"""
import sys
import os

# 添加backend路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import CustomNameMapping

# 数据库配置
DATABASE_URL = "mysql+pymysql://root:e0237e873f08ad0b@101.35.224.59:3306/file_link_monitor_v2?charset=utf8mb4"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# OpenList配置
OPENLIST_URL = "http://10.10.10.17:5255"
OPENLIST_TOKEN = "openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4"
PATH_PREFIX = "/A-闲鱼影视（自动更新）"

PAN_MOUNT_MAP = {
    'baidu': 'baidu',
    'quark': 'kuake',
    'xunlei': 'xunlei'
}


def get_mapping_by_name(original_name):
    """从数据库查询映射信息"""
    db = SessionLocal()
    try:
        mapping = db.query(CustomNameMapping).filter(
            CustomNameMapping.original_name == original_name
        ).first()
        
        if not mapping:
            return None
        
        return {
            'id': mapping.id,
            'original_name': mapping.original_name,
            'category': mapping.category,
            'xunlei_name': mapping.xunlei_name,
            'quark_name': mapping.quark_name,
            'baidu_name': mapping.baidu_name,
            'xunlei_link': mapping.xunlei_link,
            'quark_link': mapping.quark_link,
            'baidu_link': mapping.baidu_link,
        }
    finally:
        db.close()


def build_path_from_category(category):
    """根据 category 构建完整路径"""
    if not category:
        raise Exception("category 为空")
    return f"{PATH_PREFIX}/{category}"


def get_openlist_files(pan_type, path):
    """通过OpenList获取文件列表"""
    import requests
    
    mount_point = PAN_MOUNT_MAP.get(pan_type)
    if not mount_point:
        raise Exception(f"不支持的网盘类型: {pan_type}")
    
    full_path = f"/{mount_point}{path}"
    
    list_url = f"{OPENLIST_URL}/api/fs/list"
    headers = {
        "Authorization": OPENLIST_TOKEN,
        "Content-Type": "application/json"
    }
    body = {
        "path": full_path,
        "refresh": False,
        "page": 1,
        "per_page": 1000
    }
    
    response = requests.post(list_url, json=body, headers=headers, timeout=30)
    result = response.json()
    
    if result.get('code') != 200:
        raise Exception(f"列出目录失败: {result.get('message')}")
    
    content = result.get('data', {}).get('content', []) or []
    return content


def test_boyi():
    """测试查找"搏忆 (2025)"""
    print("="*60)
    print("测试：查找 '搏忆 (2025)' 的文件信息")
    print("="*60)
    
    original_name = "搏忆 (2025)"
    
    # 1. 查询 mapping
    print(f"\n🔍 步骤1: 查询 mapping 表...")
    mapping = get_mapping_by_name(original_name)
    
    if not mapping:
        print(f"❌ 未找到 mapping 记录: {original_name}")
        return
    
    print(f"✅ 找到 mapping 记录:")
    print(f"   ID: {mapping['id']}")
    print(f"   原始名称: {mapping['original_name']}")
    print(f"   分类: {mapping['category']}")
    print(f"   迅雷名称: {mapping['xunlei_name']}")
    print(f"   夸克名称: {mapping['quark_name']}")
    print(f"   百度名称: {mapping['baidu_name']}")
    print(f"   迅雷链接: {mapping['xunlei_link']}")
    
    # 2. 构建路径
    if not mapping['category']:
        print(f"❌ mapping 记录缺少 category 字段")
        return
    
    full_path = build_path_from_category(mapping['category'])
    print(f"\n📂 步骤2: 构建路径")
    print(f"   目标路径: {full_path}")
    print(f"   OpenList完整路径: /xunlei{full_path}")
    
    # 3. 检查是否有迅雷名称
    if not mapping['xunlei_name']:
        print(f"\n⚠️  mapping 记录缺少 xunlei_name 字段")
        return
    
    # 4. 通过 OpenList 查找文件
    print(f"\n🔄 步骤3: 通过 OpenList 查找文件...")
    try:
        files = get_openlist_files('xunlei', full_path)
        print(f"✅ 目录下共有 {len(files)} 个文件/文件夹")
        
        # 显示目录内容
        print(f"\n📋 目录内容（前15个）:")
        for i, file in enumerate(files[:15], 1):
            file_type = "📁" if file.get('is_dir') else "📄"
            size = file.get('size', 0)
            size_str = f"({size / 1024 / 1024:.2f} MB)" if size > 0 else ""
            print(f"   {i}. {file_type} {file.get('name')} {size_str}")
        
        # 查找匹配的文件
        target_name = mapping['xunlei_name']
        print(f"\n🔍 查找目标文件: {target_name}")
        
        matched_files = []
        for file in files:
            file_name = file.get('name', '')
            # 精确匹配
            if file_name == target_name:
                matched_files.append((file, 'exact'))
            # 模糊匹配（包含关键词）
            elif target_name in file_name and not file.get('is_dir'):
                matched_files.append((file, 'fuzzy'))
        
        if matched_files:
            print(f"✅ 找到 {len(matched_files)} 个匹配文件:")
            for i, (file, match_type) in enumerate(matched_files, 1):
                match_label = "精确匹配" if match_type == 'exact' else "模糊匹配"
                file_id = file.get('id', '')
                size = file.get('size', 0)
                size_str = f"{size / 1024 / 1024:.2f} MB" if size > 0 else ""
                print(f"   {i}. [{match_label}] {file.get('name')}")
                print(f"      文件ID: {file_id}")
                print(f"      大小: {size_str}")
        else:
            print(f"❌ 未找到匹配文件")
            print(f"   提示: 请检查 xunlei_name 是否与实际文件名匹配")
        
    except Exception as e:
        print(f"❌ OpenList 查询失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)


if __name__ == '__main__':
    test_boyi()

