"""
测试使用Playwright + Cookie获取迅雷网盘的x-captcha-token
Playwright的page.request会自动处理x-captcha-token
"""
from playwright.sync_api import sync_playwright
import time
import json

# 迅雷Cookie（从浏览器导出的JSON格式）
XUNLEI_COOKIES = [
    {
        "name": "XLA_CI",
        "value": "5ae70956cf5eb5acc2644c1ded0e22fd",
        "domain": ".xunlei.com",
        "path": "/"
    },
    {
        "name": "deviceid",
        "value": "wdi10.d765a49124d0b4c8d593d73daa738f51134146e64398f5f02515b17ad857699e",
        "domain": ".xunlei.com",
        "path": "/"
    },
    {
        "name": "xl_fp_rt",
        "value": "1766145394275",
        "domain": ".xunlei.com",
        "path": "/"
    },
    {
        "name": "sessionid",
        "value": "cs001.3480B930C7A49B0671DC7FAB26763D02",
        "domain": ".xunlei.com",
        "path": "/"
    },
    {
        "name": "userid",
        "value": "683676213",
        "domain": ".xunlei.com",
        "path": "/"
    },
    {
        "name": "usernewno",
        "value": "1270048342",
        "domain": ".xunlei.com",
        "path": "/"
    }
]

USER_ID = "683676213"  # 你的用户ID

def test_xunlei_with_playwright():
    """使用Playwright的request API自动处理token"""
    
    print("=" * 60)
    print("启动Playwright浏览器...")
    print("=" * 60)
    
    with sync_playwright() as p:
        # 启动浏览器（有头模式，可以看到窗口）
        print("\n🌐 启动Chrome浏览器...")
        browser = p.chromium.launch(headless=False)
        
        # 创建上下文并设置Cookie
        print("\n🍪 设置Cookie登录...")
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        context.add_cookies(XUNLEI_COOKIES)
        
        page = context.new_page()
        
        # 用于存储捕获的认证信息
        captured_auth = {
            'authorization': None,
            'x-captcha-token': None
        }
        
        # 监听所有请求，提取认证信息
        def handle_request(request):
            headers = request.headers
            # 只捕获迅雷API请求的header
            if 'api-pan.xunlei.com' in request.url or 'api-gateway-pan.xunlei.com' in request.url:
                if 'authorization' in headers and not captured_auth['authorization']:
                    captured_auth['authorization'] = headers['authorization']
                    print(f"   ✅ 捕获到 authorization: {headers['authorization'][:80]}...")
                if 'x-captcha-token' in headers and not captured_auth['x-captcha-token']:
                    captured_auth['x-captcha-token'] = headers['x-captcha-token']
                    print(f"   ✅ 捕获到 x-captcha-token: {headers['x-captcha-token'][:80]}...")
        
        page.on('request', handle_request)
        
        # 打开迅雷网盘
        print("\n📱 打开迅雷网盘...")
        page.goto('https://pan.xunlei.com')
        
        print("\n🔍 等待捕获认证信息...")
        # 等待最多15秒，直到两个token都捕获到
        max_wait = 15
        waited = 0
        while waited < max_wait:
            if captured_auth['authorization'] and captured_auth['x-captcha-token']:
                break
            time.sleep(1)
            waited += 1
            if waited % 3 == 0:
                print(f"   等待中... ({waited}s) authorization:{'✅' if captured_auth['authorization'] else '❌'} x-captcha-token:{'✅' if captured_auth['x-captcha-token'] else '❌'}")
        
        # 如果还没捕获到，刷新一下
        if not captured_auth['x-captcha-token'] or not captured_auth['authorization']:
            print("   🔄 刷新页面重新捕获...")
            captured_auth['x-captcha-token'] = None
            captured_auth['authorization'] = None
            page.reload()
            time.sleep(5)
        
        # 定义获取新token的函数
        def get_fresh_token():
            """刷新页面获取新的x-captcha-token"""
            print("   🔄 刷新页面获取新token...")
            captured_auth['x-captcha-token'] = None
            captured_auth['authorization'] = None
            
            page.reload()
            
            # 等待最多8秒捕获新token
            max_wait = 8
            waited = 0
            while waited < max_wait:
                if captured_auth['authorization'] and captured_auth['x-captcha-token']:
                    break
                time.sleep(0.5)
                waited += 0.5
            
            if not captured_auth['x-captcha-token'] or not captured_auth['authorization']:
                print("   ⚠️  未捕获到新token")
                return False
            
            print(f"   ✅ 获取到新token")
            return True
        
        # 检查是否成功捕获初始token
        if not captured_auth['x-captcha-token'] or not captured_auth['authorization']:
            print("\n❌ 未能捕获到完整的认证信息")
            print(f"   authorization: {'✅' if captured_auth['authorization'] else '❌'}")
            print(f"   x-captcha-token: {'✅' if captured_auth['x-captcha-token'] else '❌'}")
            print("\n按回车键关闭浏览器...")
            input()
            browser.close()
            return
        
        print("\n" + "=" * 60)
        print("🧪 测试1: 获取token后立即搜索")
        print("=" * 60)
        
        # 使用捕获到的token手动构造请求
        import requests
        file_id = None
        
        try:
            headers = {
                'accept': '*/*',
                'authorization': captured_auth['authorization'],
                'x-captcha-token': captured_auth['x-captcha-token'],
                'x-client-id': 'Xqp0kJBXWhwaTpB6',
                'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            print(f"   使用token: {captured_auth['x-captcha-token'][:60]}...")
            
            params = {
                "keyword": "A-闲鱼影视（自动更新）",
                "limit": "20",
                "space": "*",
                "user_id": USER_ID,
                "parent_id": "",
                "page_token": ""
            }
            
            resp = requests.get(
                "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search",
                params=params,
                headers=headers,
                timeout=10
            )
            
            print(f"   状态码: {resp.status_code}")
            data = resp.json()
            
            if data.get('code') == 0:
                files = data.get('data', {}).get('files', [])
                print(f"   ✅ 搜索成功! 找到 {len(files)} 个结果")
                if files:
                    file_id = files[0].get('id')
                    print(f"   文件ID: {file_id}")
            else:
                print(f"   ❌ 搜索失败: {data.get('message')}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
        
        # 测试2: 用同一个token连续执行5组搜索+分享
        print("\n" + "=" * 60)
        print("🧪 测试2: 用同一个token连续执行5组搜索+分享")
        print("=" * 60)
        print("   ⚠️  不刷新token，测试token的有效次数")
        
        success_pairs = 0
        token_used = captured_auth['x-captcha-token']
        print(f"   使用token: {token_used[:60]}...")
        
        for i in range(5):
            print(f"\n--- 第 {i+1} 组 ---")
            
            # 搜索
            try:
                headers = {
                    'accept': '*/*',
                    'authorization': captured_auth['authorization'],
                    'x-captcha-token': token_used,
                    'x-client-id': 'Xqp0kJBXWhwaTpB6',
                    'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
                    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                params = {
                    "keyword": "A-闲鱼影视（自动更新）",
                    "limit": "20",
                    "space": "*",
                    "user_id": USER_ID,
                    "parent_id": "",
                    "page_token": ""
                }
                
                resp = requests.get(
                    "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search",
                    params=params,
                    headers=headers,
                    timeout=10
                )
                
                data = resp.json()
                
                if data.get('code') == 0:
                    files = data.get('data', {}).get('files', [])
                    print(f"   搜索: ✅ 找到 {len(files)} 个结果")
                    
                    if files:
                        file_id = files[0].get('id')
                        
                        # 创建分享
                        share_headers = headers.copy()
                        share_headers['content-type'] = 'application/json'
                        
                        share_data_body = {
                            "file_ids": [file_id],
                            "share_to": "copy",
                            "params": {
                                "subscribe_push": "false",
                                "WithPassCodeInLink": "true"
                            },
                            "title": "云盘资源分享",
                            "restore_limit": "-1",
                            "expiration_days": "-1"
                        }
                        
                        share_resp = requests.post(
                            "https://api-pan.xunlei.com/drive/v1/share",
                            json=share_data_body,
                            headers=share_headers,
                            timeout=10
                        )
                        
                        share_data = share_resp.json()
                        
                        if share_data.get('share_url'):
                            print(f"   分享: ✅ {share_data['share_url']} (提取码: {share_data.get('pass_code', '')})")
                            success_pairs += 1
                        else:
                            print(f"   分享: ❌ {share_data.get('error_description', share_data.get('message'))}")
                            break  # 失败了就停止
                else:
                    print(f"   搜索: ❌ {data.get('message')}")
                    break  # 失败了就停止
                    
            except Exception as e:
                print(f"   ❌ 异常: {e}")
                break
        
        print(f"\n💡 结论: 同一个token成功完成了 {success_pairs}/5 组搜索+分享操作")
        
        # 测试3: 使用刷新token的方式连续请求
        print("\n" + "=" * 60)
        print("🧪 测试3: 每次刷新token，连续3组搜索+分享")
        print("=" * 60)
        
        success_count = 0
        for i in range(5):
            print(f"\n第 {i+1} 次请求:")
            
            # 每次请求前获取新token
            if not get_fresh_token():
                print("   ❌ 无法获取新token")
                continue
            
            try:
                headers = {
                    'accept': '*/*',
                    'authorization': captured_auth['authorization'],
                    'x-captcha-token': captured_auth['x-captcha-token'],
                    'x-client-id': 'Xqp0kJBXWhwaTpB6',
                    'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
                    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                params = {
                    "keyword": "A-闲鱼影视（自动更新）",
                    "limit": "20",
                    "space": "*",
                    "user_id": USER_ID,
                    "parent_id": "",
                    "page_token": ""
                }
                
                resp = requests.get(
                    "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search",
                    params=params,
                    headers=headers,
                    timeout=10
                )
                
                data = resp.json()
                if data.get('code') == 0:
                    files = data.get('data', {}).get('files', [])
                    print(f"   ✅ 成功! 找到 {len(files)} 个结果")
                    success_count += 1
                else:
                    print(f"   ❌ 失败: {data.get('message')}")
            except Exception as e:
                print(f"   ❌ 异常: {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 测试完成! 成功率: {success_count}/5")
        print("=" * 60)
        
        if success_count == 5:
            print("\n🎉 完美! Playwright可以稳定处理x-captcha-token")
            print("   建议: 使用Playwright方案实现迅雷API")
        elif success_count > 0:
            print(f"\n⚠️  部分成功 ({success_count}/5)")
            print("   可能需要调整请求间隔或重试机制")
        else:
            print("\n❌ 全部失败，可能是:")
            print("   1. Cookie已过期，需要重新登录")
            print("   2. USER_ID不正确")
            print("   3. 网络问题")
        
        print("\n按回车键关闭浏览器...")
        input()
        
        browser.close()

if __name__ == '__main__':
    print("\n提示: 请先修改脚本顶部的 XUNLEI_COOKIE 和 USER_ID")
    print("      或直接运行，在打开的浏览器中登录\n")
    test_xunlei_with_playwright()
