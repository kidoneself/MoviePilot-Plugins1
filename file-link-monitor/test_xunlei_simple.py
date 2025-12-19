"""
简化测试：登录 → 获取token → 搜索 → 创建分享
"""
from playwright.sync_api import sync_playwright
import time
import json
import requests

# 迅雷Cookie
XUNLEI_COOKIES = [
    {"name": "XLA_CI", "value": "5ae70956cf5eb5acc2644c1ded0e22fd", "domain": ".xunlei.com", "path": "/"},
    {"name": "deviceid", "value": "wdi10.d765a49124d0b4c8d593d73daa738f51134146e64398f5f02515b17ad857699e", "domain": ".xunlei.com", "path": "/"},
    {"name": "xl_fp_rt", "value": "1766145394275", "domain": ".xunlei.com", "path": "/"},
    {"name": "sessionid", "value": "cs001.3480B930C7A49B0671DC7FAB26763D02", "domain": ".xunlei.com", "path": "/"},
    {"name": "userid", "value": "683676213", "domain": ".xunlei.com", "path": "/"},
    {"name": "usernewno", "value": "1270048342", "domain": ".xunlei.com", "path": "/"}
]

USER_ID = "683676213"

def main():
    print("=" * 60)
    print("迅雷API测试：一个token完成搜索+分享")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.add_cookies(XUNLEI_COOKIES)
        page = context.new_page()
        
        # 用于捕获token
        auth_info = {'authorization': None, 'x-captcha-token': None}
        
        def capture_token(request):
            headers = request.headers
            if 'api-pan.xunlei.com' in request.url or 'api-gateway-pan.xunlei.com' in request.url:
                if 'authorization' in headers:
                    auth_info['authorization'] = headers['authorization']
                if 'x-captcha-token' in headers:
                    auth_info['x-captcha-token'] = headers['x-captcha-token']
        
        page.on('request', capture_token)
        
        # 1. 登录并刷新获取token
        print("\n1️⃣ 打开迅雷网盘并刷新...")
        page.goto('https://pan.xunlei.com')
        time.sleep(2)
        page.reload()
        
        # 等待token
        print("   等待捕获token...")
        for _ in range(10):
            if auth_info['authorization'] and auth_info['x-captcha-token']:
                break
            time.sleep(0.5)
        
        if not auth_info['authorization'] or not auth_info['x-captcha-token']:
            print("   ❌ 未能获取到token")
            browser.close()
            return
        
        print(f"   ✅ authorization: {auth_info['authorization'][:60]}...")
        print(f"   ✅ x-captcha-token: {auth_info['x-captcha-token'][:60]}...")
        
        # 2. 搜索文件
        print("\n2️⃣ 使用token搜索文件...")
        headers = {
            'authorization': auth_info['authorization'],
            'x-captcha-token': auth_info['x-captcha-token'],
            'x-client-id': 'Xqp0kJBXWhwaTpB6',
            'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
        }
        
        resp = requests.get(
            "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search",
            params={
                "keyword": "A-闲鱼影视（自动更新）",
                "limit": "20",
                "space": "*",
                "user_id": USER_ID,
                "parent_id": "",
                "page_token": ""
            },
            headers=headers,
            timeout=10
        )
        
        search_data = resp.json()
        
        if search_data.get('code') == 0:
            files = search_data.get('data', {}).get('files', [])
            print(f"   ✅ 搜索成功! 找到 {len(files)} 个结果")
            
            if not files:
                print("   ❌ 没有找到文件")
                browser.close()
                return
            
            file_id = files[0].get('id')
            file_name = files[0].get('name')
            print(f"   文件: {file_name}")
            print(f"   ID: {file_id}")
            
            # 3. 创建分享（用同一个token）
            print("\n3️⃣ 使用同一个token创建分享...")
            print(f"   token: {auth_info['x-captcha-token'][:60]}...")
            
            share_headers = headers.copy()
            share_headers['content-type'] = 'application/json'
            
            share_resp = requests.post(
                "https://api-pan.xunlei.com/drive/v1/share",
                json={
                    "file_ids": [file_id],
                    "share_to": "copy",
                    "params": {
                        "subscribe_push": "false",
                        "WithPassCodeInLink": "true"
                    },
                    "title": "云盘资源分享",
                    "restore_limit": "-1",
                    "expiration_days": "-1"
                },
                headers=share_headers,
                timeout=10
            )
            
            share_data = share_resp.json()
            
            if share_data.get('share_url'):
                print(f"   ✅ 分享成功!")
                print(f"   链接: {share_data['share_url']}")
                print(f"   提取码: {share_data.get('pass_code', '')}")
                print("\n" + "=" * 60)
                print("🎉 结论: 一个token可以完成搜索+分享操作!")
                print("=" * 60)
            else:
                print(f"   ❌ 分享失败")
                print(f"   错误: {share_data}")
        else:
            print(f"   ❌ 搜索失败: {search_data.get('message')}")
        
        print("\n按回车关闭浏览器...")
        input()
        browser.close()

if __name__ == '__main__':
    main()
