#!/usr/bin/env python3
"""
迅雷网盘API调用示例
演示如何获取文件列表、搜索文件、创建分享链接
支持通过OpenList获取文件ID
支持从mapping表自动查找文件路径
"""
import requests
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# 添加backend路径以导入models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.models import CustomNameMapping, PanCookie
from backend.utils.xunlei_api import XunleiAPI, _browser_manager

# ============================================================
# 数据库配置
# ============================================================
DATABASE_URL = "mysql+pymysql://root:e0237e873f08ad0b@101.35.224.59:3306/file_link_monitor_v2?charset=utf8mb4"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# ============================================================
# OpenList配置
# ============================================================
OPENLIST_URL = "http://10.10.10.17:5255"
OPENLIST_TOKEN = "openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4"

# 网盘挂载点
PAN_MOUNT_MAP = {
    'baidu': 'baidu',
    'quark': 'kuake',
    'xunlei': 'xunlei'
}

# 目录前缀（注意：xunlei 挂载点会自动添加，这里只需要写挂载点之后的路径）
PATH_PREFIX = "/A-闲鱼影视（自动更新）"


# ============================================================
# 从数据库查询映射信息
# ============================================================
def get_mapping_by_name(original_name):
    """
    从数据库查询映射信息
    
    Args:
        original_name: 原始名称
    
    Returns:
        dict: 包含 category, xunlei_name 等信息，未找到返回 None
    """
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
            'category': mapping.category,  # 如: 剧集/国产剧集
            'xunlei_name': mapping.xunlei_name,
            'quark_name': mapping.quark_name,
            'baidu_name': mapping.baidu_name,
            'xunlei_link': mapping.xunlei_link,
        }
    finally:
        db.close()


def build_path_from_category(category):
    """
    根据 category 构建完整路径
    
    Args:
        category: 二级分类，如 "剧集/国产剧集" 或 "电影/国产电影"
    
    Returns:
        str: 完整路径，如 "/A-闲鱼影视（自动更新）/剧集/国产剧集"
        
    说明：
        - OpenList 会自动添加挂载点 (xunlei)
        - 最终完整路径：/xunlei/A-闲鱼影视（自动更新）/剧集/国产剧集
    """
    if not category:
        raise Exception("category 为空")
    
    # 构建完整路径：前缀 + category
    full_path = f"{PATH_PREFIX}/{category}"
    return full_path


def find_file_in_mapping(original_name, pan_type='xunlei'):
    """
    通过 mapping 表查找文件
    
    流程：
    1. 从数据库查询 mapping 信息
    2. 根据 category 构建路径
    3. 在该路径下通过 OpenList 查找文件
    4. 返回文件ID
    
    Args:
        original_name: 原始名称（mapping表中的记录）
        pan_type: 网盘类型，默认 'xunlei'
    
    Returns:
        tuple: (file_id, full_path, filename) 或 (None, None, None)
    
    示例：
        file_id, path, name = find_file_in_mapping("大圣归来")
        # 返回: ("xxx", "/A-闲鱼影视（自动更新）/电影/国产电影", "大圣归来 4K")
        # 在 OpenList 中的完整路径: /xunlei/A-闲鱼影视（自动更新）/电影/国产电影
    """
    # 1. 查询 mapping
    print(f"🔍 查询 mapping 表: {original_name}")
    mapping = get_mapping_by_name(original_name)
    
    if not mapping:
        print(f"❌ 未找到 mapping 记录: {original_name}")
        return None, None, None
    
    print(f"✅ 找到 mapping 记录:")
    print(f"   ID: {mapping['id']}")
    print(f"   分类: {mapping['category']}")
    print(f"   迅雷名称: {mapping['xunlei_name']}")
    
    # 2. 构建路径
    if not mapping['category']:
        print(f"❌ mapping 记录缺少 category 字段")
        return None, None, None
    
    full_path = build_path_from_category(mapping['category'])
    print(f"📂 目标路径: {full_path}")
    print(f"   (OpenList完整路径: /{PAN_MOUNT_MAP[pan_type]}{full_path})")
    
    # 3. 获取网盘显示名
    filename = mapping.get(f'{pan_type}_name')
    if not filename:
        print(f"❌ mapping 记录缺少 {pan_type}_name 字段")
        return None, None, None
    
    print(f"📄 目标文件名: {filename}")
    
    # 4. 通过 OpenList 查找文件ID
    print(f"🔄 在 OpenList 中查找文件...")
    file_id = find_file_id_by_name(pan_type, full_path, filename)
    
    if file_id:
        return file_id, full_path, filename
    else:
        return None, full_path, filename


# ============================================================
# 通过OpenList获取文件列表
# ============================================================
def get_files_from_openlist(pan_type, path):
    """
    通过OpenList获取指定路径下的文件列表
    
    Args:
        pan_type: 网盘类型 'baidu', 'quark', 'xunlei'
        path: 用户路径，如 '/A-闲鱼影视/电影'
    
    Returns:
        list: 文件列表，每个文件包含 id, name, is_dir 等字段
    """
    mount_point = PAN_MOUNT_MAP.get(pan_type)
    if not mount_point:
        raise Exception(f"不支持的网盘类型: {pan_type}")
    
    # 构建完整路径
    full_path = f"/{mount_point}{path}"
    
    # 调用OpenList API
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


def find_file_id_by_name(pan_type, path, filename):
    """
    通过OpenList查找指定文件名的文件ID
    
    Args:
        pan_type: 网盘类型 'baidu', 'quark', 'xunlei'
        path: 文件所在目录路径
        filename: 文件名（支持精确匹配或模糊匹配）
    
    Returns:
        str: 文件ID，如果找不到返回None
    
    示例：
        # 精确匹配
        file_id = find_file_id_by_name("xunlei", "/A-闲鱼影视/电影", "泰坦尼克号.mkv")
        
        # 模糊匹配（包含关键词）
        file_id = find_file_id_by_name("xunlei", "/A-闲鱼影视/电影", "泰坦尼克号")
    """
    files = get_files_from_openlist(pan_type, path)
    
    print(f"\n📂 在 {path} 目录下找到 {len(files)} 个文件/文件夹")
    
    # 先尝试精确匹配
    for file in files:
        file_name = file.get('name', '')
        if file_name == filename:
            file_id = file.get('id', '')
            print(f"✅ 精确匹配: {file_name}")
            print(f"   文件ID: {file_id}")
            return file_id
    
    # 如果精确匹配失败，尝试模糊匹配（文件名包含关键词）
    matched_files = []
    for file in files:
        file_name = file.get('name', '')
        # 跳过文件夹
        if file.get('is_dir'):
            continue
        # 包含关键词
        if filename in file_name:
            matched_files.append(file)
    
    if matched_files:
        # 如果有多个匹配，返回第一个
        file = matched_files[0]
        file_id = file.get('id', '')
        file_name = file.get('name', '')
        print(f"✅ 模糊匹配: {file_name}")
        print(f"   文件ID: {file_id}")
        if len(matched_files) > 1:
            print(f"⚠️  找到 {len(matched_files)} 个匹配文件，使用第一个")
            for i, f in enumerate(matched_files[:5], 1):
                print(f"   {i}. {f.get('name')}")
        return file_id
    
    print(f"❌ 未找到文件: {filename}")
    print(f"   目录下的文件:")
    for i, file in enumerate(files[:10], 1):
        file_type = "📁" if file.get('is_dir') else "📄"
        print(f"   {i}. {file_type} {file.get('name')}")
    
    return None


# ============================================================
# 获取认证Token
# ============================================================
def get_xunlei_tokens(cookies_list):
    """
    使用Playwright访问迅雷网盘，捕获认证token
    
    Args:
        cookies_list: Cookie列表，格式如下：
        [
            {"name": "sessionid", "value": "xxx", "domain": ".xunlei.com", "path": "/"},
            {"name": "userid", "value": "123456", "domain": ".xunlei.com", "path": "/"},
            ...
        ]
    
    Returns:
        dict: {"authorization": "xxx", "x-captcha-token": "xxx"}
    """
    captured_tokens = {
        'authorization': None,
        'x-captcha-token': None
    }
    
    def capture_request(request):
        """监听网络请求，捕获token"""
        headers = request.headers
        if 'api-pan.xunlei.com' in request.url or 'api-gateway-pan.xunlei.com' in request.url:
            if 'authorization' in headers:
                captured_tokens['authorization'] = headers['authorization']
            if 'x-captcha-token' in headers:
                captured_tokens['x-captcha-token'] = headers['x-captcha-token']
    
    with sync_playwright() as p:
        # 启动浏览器（无头模式）
        browser = p.chromium.launch(headless=True)
        
        # 创建上下文并设置Cookie
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        context.add_cookies(cookies_list)
        
        # 创建页面并监听请求
        page = context.new_page()
        page.on('request', capture_request)
        
        # 访问迅雷网盘，触发API请求
        page.goto('https://pan.xunlei.com', wait_until='networkidle', timeout=30000)
        
        browser.close()
    
    return captured_tokens


# ============================================================
# 创建分享链接
# ============================================================
def create_share_link(auth_token, captcha_token, file_id):
    """
    创建分享链接
    
    Args:
        auth_token: 认证token
        captcha_token: 验证token
        file_id: 文件/文件夹ID
    
    Returns:
        dict: {"share_url": "xxx", "pass_code": "xxx"}
    """
    url = "https://api-pan.xunlei.com/drive/v1/share"
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': auth_token,
        'x-captcha-token': captcha_token,
        'x-client-id': 'Xqp0kJBXWhwaTpB6',
        'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    data = {
        "file_ids": [file_id],
        "share_to": "copy",
        "params": {
            "subscribe_push": "false",
            "WithPassCodeInLink": "true"
        },
        "title": "云盘资源分享",
        "restore_limit": "-1",     # -1表示不限制转存次数
        "expiration_days": "-1"     # -1表示永久有效
    }
    
    response = requests.post(url, json=data, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"创建分享链接失败: {response.status_code}")
    
    result = response.json()
    return {
        "share_url": result.get('share_url'),
        "pass_code": result.get('pass_code')
    }


# ============================================================
# 使用示例
# ============================================================
if __name__ == '__main__':
    # 1. 准备Cookie（从浏览器中导出）
    cookies = [
        {"name": "sessionid", "value": "your_session_id", "domain": ".xunlei.com", "path": "/"},
        {"name": "userid", "value": "your_user_id", "domain": ".xunlei.com", "path": "/"},
        {"name": "deviceid", "value": "your_device_id", "domain": ".xunlei.com", "path": "/"},
        {"name": "XLA_CI", "value": "your_xla_ci", "domain": ".xunlei.com", "path": "/"},
    ]
    
    print("="*60)
    print("迅雷网盘 - 通过Mapping表自动查找并创建分享链接")
    print("="*60)
    
    # ============ 方法：通过 mapping 表自动查找 ============
    
    # 1. 从 mapping 表查找文件
    print("\n🔄 步骤1: 从 mapping 表查找文件...")
    original_name = "大圣归来"  # 修改为你要查找的剧名/电影名
    pan_type = "xunlei"
    
    file_id, full_path, filename = find_file_in_mapping(original_name, pan_type)
    
    if not file_id:
        print(f"\n❌ 未找到文件，请检查:")
        print(f"   1. mapping 表中是否存在记录: {original_name}")
        print(f"   2. mapping 记录是否有 category 字段")
        print(f"   3. mapping 记录是否有 {pan_type}_name 字段")
        if full_path:
            print(f"   4. OpenList 路径是否正确: {full_path}")
            print(f"   5. 文件名是否匹配: {filename}")
        exit(1)
    
    print(f"\n✅ 成功找到文件!")
    print(f"   文件ID: {file_id}")
    print(f"   路径: {full_path}")
    print(f"   文件名: {filename}")
    
    # 2. 获取认证Token
    print("\n🔄 步骤2: 获取认证Token...")
    tokens = get_xunlei_tokens(cookies)
    print(f"✅ Authorization: {tokens['authorization'][:50]}...")
    print(f"✅ X-Captcha-Token: {tokens['x-captcha-token'][:50]}...")
    
    # 3. 创建分享链接
    print("\n🔄 步骤3: 创建分享链接...")
    try:
        share = create_share_link(tokens['authorization'], tokens['x-captcha-token'], file_id)
        print(f"\n{'='*60}")
        print("✅ 分享链接创建成功！")
        print(f"{'='*60}")
        print(f"📺 剧名: {original_name}")
        print(f"📄 文件名: {filename}")
        print(f"🔗 分享链接: {share['share_url']}")
        print(f"🔑 提取码: {share['pass_code']}")
        print(f"📋 完整链接: {share['share_url']}?pwd={share['pass_code']}")
        print(f"{'='*60}")
    except Exception as e:
        print(f"❌ 创建分享链接失败: {e}")


# ============================================================
# 快捷函数：通过 mapping 一步到位创建分享链接
# ============================================================
def create_share_from_mapping(cookies, original_name, pan_type='xunlei'):
    """
    通过 mapping 表一步到位创建分享链接
    
    流程：
    1. 从 mapping 表查询文件信息和路径
    2. 通过 OpenList 获取文件ID
    3. 获取认证Token
    4. 创建分享链接
    
    Args:
        cookies: Cookie列表
        original_name: 原始名称（mapping表中的记录）
        pan_type: 网盘类型，默认 'xunlei'
    
    Returns:
        dict: {"share_url": "xxx", "pass_code": "xxx", "filename": "xxx"} 或 None
    
    示例:
        share = create_share_from_mapping(
            cookies=[...],
            original_name="大圣归来",
            pan_type="xunlei"
        )
        if share:
            print(f"分享链接: {share['share_url']}?pwd={share['pass_code']}")
            print(f"文件名: {share['filename']}")
    """
    try:
        # 1. 从 mapping 查找文件ID
        print(f"🔄 从 mapping 表查找: {original_name}")
        file_id, full_path, filename = find_file_in_mapping(original_name, pan_type)
        
        if not file_id:
            print(f"❌ 未找到文件")
            return None
        
        print(f"✅ 找到文件: {filename}")
        print(f"   路径: {full_path}")
        print(f"   文件ID: {file_id}")
        
        # 2. 获取认证Token
        print(f"\n🔄 获取认证Token...")
        tokens = get_xunlei_tokens(cookies)
        
        # 3. 创建分享链接
        print(f"🔄 创建分享链接...")
        share = create_share_link(tokens['authorization'], tokens['x-captcha-token'], file_id)
        
        share['filename'] = filename
        share['original_name'] = original_name
        share['path'] = full_path
        
        print(f"\n{'='*60}")
        print(f"✅ 成功！")
        print(f"{'='*60}")
        print(f"📺 剧名: {original_name}")
        print(f"📄 文件名: {filename}")
        print(f"🔗 链接: {share['share_url']}?pwd={share['pass_code']}")
        print(f"{'='*60}")
        
        return share
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return None



