#!/usr/bin/env python3
"""
使用Playwright自动获取迅雷网盘token并更新到数据库
"""
import sys
import os
import json
import time
import yaml
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from models import init_database, get_session, PanCookie

# 加载配置
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 初始化数据库
engine = init_database(config['database'])
db_session = get_session(engine)

print("="*60)
print("迅雷网盘Token自动获取")
print("="*60)

# 读取现有的迅雷Cookie（浏览器格式）
xunlei_record = db_session.query(PanCookie).filter_by(pan_type='xunlei', is_active=True).first()

if not xunlei_record:
    print("❌ 数据库中没有迅雷Cookie记录")
    print("请先在数据库中添加迅雷的浏览器Cookie")
    exit(1)

# 解析Cookie（支持浏览器格式list或API格式dict）
try:
    cookie_data = json.loads(xunlei_record.cookie)
    
    # 如果是API格式的dict，说明之前已经转换过，需要重新获取浏览器Cookie
    if isinstance(cookie_data, dict):
        print("⚠️  当前存储的是API格式token（已过期）")
        print("请提供新的浏览器Cookie列表，或手动更新数据库")
        print("\n提示：从浏览器导出Cookie，格式为JSON列表")
        print("或者运行其他工具重新获取浏览器Cookie")
        exit(1)
    
    if not isinstance(cookie_data, list):
        print("❌ Cookie格式错误，应该是列表格式")
        exit(1)
    
    print(f"✅ 读取到 {len(cookie_data)} 个Cookie")
    
    # 转换为Playwright格式
    playwright_cookies = []
    for cookie in cookie_data:
        pw_cookie = {
            'name': cookie['name'],
            'value': cookie['value'],
            'domain': cookie.get('domain', '.xunlei.com'),
            'path': cookie.get('path', '/'),
        }
        if 'expirationDate' in cookie:
            pw_cookie['expires'] = cookie['expirationDate']
        
        playwright_cookies.append(pw_cookie)
    
except Exception as e:
    print(f"❌ 解析Cookie失败: {e}")
    exit(1)

print("\n启动浏览器获取token...")
print("提示: 浏览器将自动打开迅雷网盘页面，请等待...")
print()

# 使用Playwright获取token
captured_tokens = {
    'authorization': None,
    'x_captcha_token': None,
    'x_client_id': None,
    'x_device_id': None
}

def capture_request(request):
    """捕获请求中的token"""
    headers = request.headers
    
    if 'api-pan.xunlei.com' in request.url:
        if 'authorization' in headers and not captured_tokens['authorization']:
            captured_tokens['authorization'] = headers['authorization']
            print(f"✅ 捕获到 authorization: {headers['authorization'][:50]}...")
        
        if 'x-captcha-token' in headers and not captured_tokens['x_captcha_token']:
            captured_tokens['x_captcha_token'] = headers['x-captcha-token']
            print(f"✅ 捕获到 x-captcha-token: {headers['x-captcha-token'][:50]}...")
        
        if 'x-client-id' in headers and not captured_tokens['x_client_id']:
            captured_tokens['x_client_id'] = headers['x-client-id']
            print(f"✅ 捕获到 x-client-id: {headers['x-client-id']}")
        
        if 'x-device-id' in headers and not captured_tokens['x_device_id']:
            captured_tokens['x_device_id'] = headers['x-device-id']
            print(f"✅ 捕获到 x-device-id: {headers['x-device-id']}")

try:
    with sync_playwright() as p:
        # 启动浏览器（有头模式，方便观察）
        browser = p.chromium.launch(headless=False)
        
        # 创建上下文并设置Cookie
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        )
        
        context.add_cookies(playwright_cookies)
        
        # 创建页面并监听请求
        page = context.new_page()
        page.on('request', capture_request)
        
        # 访问迅雷网盘
        print("🌐 访问迅雷网盘页面...")
        page.goto('https://pan.xunlei.com', wait_until='networkidle')
        
        print("\n等待5秒，捕获API请求...")
        time.sleep(5)
        
        # 尝试访问文件列表页面，触发更多API请求
        try:
            print("📂 访问文件列表页面...")
            page.goto('https://pan.xunlei.com/drive/home', wait_until='networkidle')
            time.sleep(3)
        except:
            pass
        
        browser.close()
        
except Exception as e:
    print(f"\n❌ 浏览器操作失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 检查是否成功获取token
print("\n" + "="*60)
print("Token获取结果")
print("="*60)

required_tokens = ['authorization', 'x_captcha_token', 'x_device_id']
missing_tokens = []

for token_name in required_tokens:
    if captured_tokens[token_name]:
        print(f"✅ {token_name}: {captured_tokens[token_name][:50]}...")
    else:
        print(f"❌ {token_name}: 未获取到")
        missing_tokens.append(token_name)

if missing_tokens:
    print(f"\n⚠️  缺少必需的token: {', '.join(missing_tokens)}")
    print("\n可能的原因:")
    print("  1. Cookie已过期，需要重新登录")
    print("  2. 网络请求被拦截")
    print("  3. 页面加载不完整")
    
    user_input = input("\n是否仍要更新已获取的token到数据库? (y/n): ")
    if user_input.lower() != 'y':
        print("已取消")
        exit(1)

# 准备新的token数据（API格式）
new_token_data = {
    'authorization': captured_tokens['authorization'],
    'x_captcha_token': captured_tokens['x_captcha_token'],
    'x_client_id': captured_tokens['x_client_id'] or 'Xqp0kJBXWhwaTpB6',  # 默认值
    'x_device_id': captured_tokens['x_device_id']
}

print("\n" + "="*60)
print("更新数据库")
print("="*60)

# 更新数据库
xunlei_record.cookie = json.dumps(new_token_data, ensure_ascii=False)
db_session.commit()

print("✅ 已更新迅雷token到数据库")
print("\n新的token数据:")
print(json.dumps(new_token_data, indent=2, ensure_ascii=False))

print("\n" + "="*60)
print("完成！现在可以使用新的token进行迅雷转存测试")
print("="*60)
