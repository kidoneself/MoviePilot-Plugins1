#!/usr/bin/env python3
"""
直接使用文件ID创建迅雷分享链接
使用后台的XunleiAPI类，但跳过搜索步骤
"""
import sys
import os
import json

# 添加backend路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import PanCookie
from backend.utils.xunlei_api import XunleiAPI, _browser_manager

# 数据库配置
DATABASE_URL = "mysql+pymysql://root:e0237e873f08ad0b@101.35.224.59:3306/file_link_monitor_v2?charset=utf8mb4"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_xunlei_cookie_from_db():
    """从数据库获取迅雷cookie"""
    db = SessionLocal()
    try:
        cookie_record = db.query(PanCookie).filter(
            PanCookie.pan_type == 'xunlei',
            PanCookie.is_active == True
        ).first()
        
        if not cookie_record:
            return None
        
        return cookie_record.cookie
    finally:
        db.close()


def create_share_with_file_id(file_id, filename="搏忆"):
    """
    使用已知的文件ID创建分享链接
    
    Args:
        file_id: 文件ID（从OpenList获取）
        filename: 文件名（用于日志）
    """
    print("="*60)
    print(f"创建迅雷分享链接 - {filename}")
    print("="*60)
    
    # 1. 从数据库获取cookie
    print("\n🔄 步骤1: 从数据库获取迅雷cookie...")
    cookie_str = get_xunlei_cookie_from_db()
    
    if not cookie_str:
        print("❌ 数据库中没有迅雷cookie")
        return None
    
    print(f"✅ 成功获取cookie")
    
    # 2. 创建XunleiAPI实例
    print("\n🔄 步骤2: 初始化XunleiAPI...")
    try:
        api = XunleiAPI(cookie_str)
        print("✅ XunleiAPI初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return None
    
    # 3. 刷新token并获取auth_info
    print("\n🔄 步骤3: 刷新token...")
    try:
        # 在浏览器线程中执行刷新操作
        def refresh_in_thread():
            page, auth_info = _browser_manager.get_page(api.cookies)
            print("   捕获现有token...")
            return api._refresh_token_sync(page, auth_info), auth_info
        
        success, auth_info = _browser_manager.run_in_thread(refresh_in_thread)
        
        if not success:
            print("❌ Token刷新失败")
            return None
        
        print(f"✅ Token刷新成功")
        print(f"   Authorization: {auth_info['authorization'][:50]}...")
        print(f"   X-Captcha-Token: {auth_info['x-captcha-token'][:50]}...")
        
    except Exception as e:
        print(f"❌ Token刷新失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 4. 直接使用文件ID创建分享链接
    print(f"\n🔄 步骤4: 创建分享链接...")
    print(f"   文件ID: {file_id}")
    
    try:
        import requests
        
        # 从cookies中提取device_id
        cookies_list = json.loads(cookie_str)
        device_id = None
        for cookie in cookies_list:
            if cookie.get('name') == 'deviceid':
                device_id = cookie.get('value', '')
                break
        
        if not device_id:
            print("❌ 无法从cookie中找到deviceid")
            return None
        
        print(f"   Device ID: {device_id[:30]}...")
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'authorization': auth_info['authorization'],
            'x-captcha-token': auth_info['x-captcha-token'],
            'x-client-id': 'Xqp0kJBXWhwaTpB6',
            'x-device-id': device_id,  # 使用cookie中的device_id
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
            "restore_limit": "-1",
            "expiration_days": "-1"
        }
        
        print(f"   请求数据: {json.dumps(data, ensure_ascii=False)}")
        
        response = requests.post(
            "https://api-pan.xunlei.com/drive/v1/share",
            json=data,
            headers=headers,
            timeout=30
        )
        
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应内容: {response.text[:200]}...")
        
        if response.status_code != 200:
            result = response.json()
            error_msg = result.get('error_description', result.get('message', '未知错误'))
            print(f"❌ 创建失败: {error_msg}")
            return None
        
        result = response.json()
        share_url = result.get('share_url')
        pass_code = result.get('pass_code', '')
        
        if not share_url:
            error_msg = result.get('error_description', result.get('message', '未知错误'))
            print(f"❌ 创建失败: {error_msg}")
            return None
        
        # 构建完整链接
        share_link = f"{share_url}?pwd={pass_code}" if pass_code else share_url
        
        print(f"\n{'='*60}")
        print("✅ 分享链接创建成功！")
        print(f"{'='*60}")
        print(f"📺 文件名: {filename}")
        print(f"📄 文件ID: {file_id}")
        print(f"🔗 分享URL: {share_url}")
        print(f"🔑 提取码: {pass_code}")
        print(f"📋 完整链接: {share_link}")
        print(f"{'='*60}")
        
        return share_link
        
    except Exception as e:
        print(f"❌ 创建分享链接失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主流程"""
    # 使用OpenList找到的搏忆文件夹ID
    file_id = "VOh_lAYLnRgZjoaaSEcByZcbA1"
    filename = "搏忆 (2025)"
    
    share_link = create_share_with_file_id(file_id, filename)
    
    if share_link:
        print("\n✅ 任务完成！")
    else:
        print("\n❌ 任务失败")


if __name__ == '__main__':
    main()

