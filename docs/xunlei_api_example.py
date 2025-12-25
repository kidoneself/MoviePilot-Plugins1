#!/usr/bin/env python3
"""
迅雷网盘API调用示例
演示如何获取文件列表、搜索文件、创建分享链接
"""
import requests
import json
from playwright.sync_api import sync_playwright

# ============================================================
# 第一步：获取认证Token
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
# 第二步：调用API获取文件列表
# ============================================================
def list_files(auth_token, captcha_token, parent_id="", page_size=100):
    """
    获取文件列表
    
    Args:
        auth_token: 认证token（从页面捕获）
        captcha_token: 验证token（从页面捕获）
        parent_id: 父文件夹ID，空字符串表示根目录
        page_size: 每页数量
    
    Returns:
        list: 文件列表
    """
    url = "https://api-pan.xunlei.com/drive/v1/files"
    
    headers = {
        'accept': '*/*',
        'authorization': auth_token,
        'x-captcha-token': captcha_token,
        'x-client-id': 'Xqp0kJBXWhwaTpB6',  # 固定值，从网页版抓取
        'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',  # 固定值
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    params = {
        "parent_id": parent_id,
        "page_size": str(page_size),
        "page": "1",
        "filters": '{"phase":{"eq":"PHASE_TYPE_COMPLETE"},"trashed":{"eq":false}}',
        "space": ""
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"请求失败: {response.status_code}, {response.text}")
    
    data = response.json()
    return data.get('files', [])


# ============================================================
# 第三步：搜索文件
# ============================================================
def search_file(auth_token, captcha_token, keyword, user_id):
    """
    搜索文件
    
    Args:
        auth_token: 认证token
        captcha_token: 验证token
        keyword: 搜索关键词
        user_id: 用户ID（从Cookie中获取）
    
    Returns:
        list: 搜索结果
    """
    url = "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search"
    
    headers = {
        'accept': '*/*',
        'authorization': auth_token,
        'x-captcha-token': captcha_token,
        'x-client-id': 'Xqp0kJBXWhwaTpB6',
        'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    params = {
        "keyword": keyword,
        "limit": "20",
        "space": "*",
        "user_id": user_id,
        "parent_id": "",
        "page_token": ""
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"搜索失败: {response.status_code}")
    
    data = response.json()
    return data.get('data', {}).get('files', [])


# ============================================================
# 第四步：创建分享链接
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
    
    # 2. 获取认证Token
    print("🔄 获取认证Token...")
    tokens = get_xunlei_tokens(cookies)
    print(f"✅ Authorization: {tokens['authorization'][:50]}...")
    print(f"✅ X-Captcha-Token: {tokens['x-captcha-token'][:50]}...")
    
    # 3. 获取文件列表
    print("\n📂 获取根目录文件列表...")
    files = list_files(tokens['authorization'], tokens['x-captcha-token'])
    for file in files:
        file_type = "📁" if file['kind'] == 'drive#folder' else "📄"
        print(f"{file_type} {file['name']}")
    
    # 4. 搜索文件
    print("\n🔍 搜索文件...")
    user_id = "your_user_id"  # 从Cookie中获取
    results = search_file(tokens['authorization'], tokens['x-captcha-token'], "关键词", user_id)
    for result in results:
        print(f"找到: {result['name']}")
    
    # 5. 创建分享链接
    print("\n📤 创建分享链接...")
    file_id = files[0]['id']  # 使用第一个文件
    share = create_share_link(tokens['authorization'], tokens['x-captcha-token'], file_id)
    print(f"✅ 分享链接: {share['share_url']}?pwd={share['pass_code']}")
    print(f"   提取码: {share['pass_code']}")

