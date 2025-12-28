#!/usr/bin/env python3
"""
夸克智能转存测试脚本

测试流程：
1. 从数据库获取Cookie
2. 解析分享URL
3. 获取文件列表（含广告标注）
4. 过滤广告
5. 获取目标文件夹ID
6. 智能选择策略
7. 调用转存API
8. 轮询任务状态
"""

import sys
import os
import time
import re
import json
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import init_database, get_session, PanCookie


# ==================== 工具函数 ====================

def convert_cookie_json_to_string(cookie_data):
    """
    将JSON格式的Cookie转换为字符串格式
    支持: JSON数组、JSON对象、字符串
    """
    # 如果已经是字符串格式，直接返回
    if isinstance(cookie_data, str):
        # 尝试解析为JSON
        try:
            cookie_data = json.loads(cookie_data)
        except:
            # 不是JSON，直接返回字符串
            return cookie_data
    
    # 如果是列表（浏览器导出格式）
    if isinstance(cookie_data, list):
        cookie_pairs = []
        for item in cookie_data:
            name = item.get('name', '')
            value = item.get('value', '')
            if name:  # 只添加有name的cookie
                cookie_pairs.append(f"{name}={value}")
        return '; '.join(cookie_pairs)
    
    # 如果是字典（API格式）
    if isinstance(cookie_data, dict):
        cookie_pairs = [f"{k}={v}" for k, v in cookie_data.items()]
        return '; '.join(cookie_pairs)
    
    return str(cookie_data)

def parse_share_url(share_url: str) -> tuple:
    """解析分享URL"""
    # 提取 pwd_id
    pwd_match = re.search(r'/s/([a-zA-Z0-9]+)', share_url)
    if not pwd_match:
        raise ValueError("无法从URL中提取pwd_id")
    pwd_id = pwd_match.group(1)
    
    # 提取 pdir_fid（在hash中）
    pdir_fid = '0'  # 默认根目录
    if '#/list/share/' in share_url:
        fid_part = share_url.split('#/list/share/')[-1].split('?')[0]
        if fid_part:
            pdir_fid = fid_part
    
    return pwd_id, pdir_fid


def is_ad_file(file_name: str, file_size: int) -> bool:
    """判断是否为广告文件"""
    AD_KEYWORDS = [
        '群', '更新', '关注', '订阅', '微信', 'qq', '频道', 
        '电报', 'telegram', '推荐', '福利', '免费', 
        '网址', '网站', '发布', '必看', '说明', '广告', 
        '二维码', '热门影视', '资源', '入群', '扫码',
        '夸克资源', '阿里资源', '百度资源', '更多资源',
        '公众号', '最新', 'vx', 'wx',
        'readme', 'read me', 'notice', 'ad', 'ads', 'adv',
        'promo', 'promotion', 'follow', 'subscribe', 
        'update', 'new', 'latest', 'channel',
        'qrcode', 'discord', 'tg'
    ]
    
    AD_EXTENSIONS = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
        '.txt', '.nfo', '.url'
    ]
    
    name_lower = file_name.lower()
    ext = None
    if '.' in name_lower:
        ext = name_lower[name_lower.rfind('.'):]
    
    # 图片类：< 5MB + 关键词
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        if file_size < 5 * 1024 * 1024:
            for keyword in AD_KEYWORDS:
                if keyword in name_lower:
                    return True
    
    # 文本类：< 500KB
    if ext in ['.txt', '.nfo', '.url']:
        if file_size < 500 * 1024:
            return True
    
    # 特定模式
    SUSPICIOUS_PATTERNS = [
        '热门影视更新', '资源更新', '最新资源',
        '关注获取', '扫码进群', '加入频道'
    ]
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in name_lower:
            return True
    
    return False


def get_stoken(cookie: str, pwd_id: str, passcode: str = '') -> str:
    """获取stoken"""
    url = 'https://drive-h.quark.cn/1/clouddrive/share/sharepage/token'
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': ''
    }
    body = {
        'pwd_id': pwd_id,
        'passcode': passcode
    }
    headers = {
        'Cookie': cookie,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://pan.quark.cn/s/{pwd_id}'
    }
    
    print(f"   请求stoken...")
    resp = requests.post(url, params=params, json=body, headers=headers)
    
    if resp.status_code != 200:
        raise Exception(f"获取stoken失败: HTTP {resp.status_code}")
    
    data = resp.json()
    if data.get('code') != 0:
        raise Exception(f"获取stoken失败: {data.get('message')}")
    
    stoken = data['data']['stoken']
    print(f"   ✅ stoken: {stoken[:20]}...")
    return stoken


def get_quark_file_list(cookie: str, pwd_id: str, stoken: str, pdir_fid: str) -> dict:
    """获取夸克分享文件列表"""
    url = 'https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail'
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': '',
        'ver': '2',
        'pwd_id': pwd_id,
        'stoken': stoken,
        'pdir_fid': pdir_fid,
        'force': '0',
        '_page': 1,
        '_size': 50,
        '_fetch_banner': 1,
        '_fetch_share': 1,
        'fetch_relate_conversation': 1,
        '_fetch_total': 1,
        '_sort': 'file_type:asc,file_name:asc'
    }
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://pan.quark.cn/s/{pwd_id}',
        'Accept': 'application/json, text/plain, */*'
    }
    
    print(f"   请求文件列表...")
    resp = requests.get(url, params=params, headers=headers)
    
    if resp.status_code != 200:
        raise Exception(f"获取文件列表失败: HTTP {resp.status_code}")
    
    data = resp.json()
    if data.get('code') != 0:
        print(f"   ❌ API返回错误: {data.get('message')}")
        raise Exception(f"获取文件列表失败: {data.get('message')}")
    
    files = data['data'].get('list', [])
    total = data['data'].get('total', len(files))
    
    print(f"   ✅ 成功获取 {len(files)} 个文件")
    
    return {
        'files': files,
        'total': total
    }


def call_quark_transfer_api(cookie: str, stoken: str, pwd_id: str, 
                           pdir_fid: str, to_pdir_fid: str, **params) -> str:
    """调用夸克转存API"""
    url = 'https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save'
    query_params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': ''
    }
    body = {
        'pwd_id': pwd_id,
        'stoken': stoken,
        'pdir_fid': pdir_fid,
        'to_pdir_fid': to_pdir_fid,
        'scene': 'link',
        **params
    }
    headers = {
        'Cookie': cookie,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://pan.quark.cn/s/{pwd_id}'
    }
    
    print(f"📤 转存参数: {body}")
    
    resp = requests.post(url, params=query_params, json=body, headers=headers)
    data = resp.json()
    
    if data.get('code') != 0:
        print(f"❌ 转存API返回错误: {data}")
        raise Exception(f"转存失败: {data.get('message')}")
    
    return data['data']['task_id']


def poll_quark_task(cookie: str, task_id: str, timeout: int = 60) -> dict:
    """轮询夸克任务状态"""
    url = 'https://drive-pc.quark.cn/1/clouddrive/task'
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    start_time = time.time()
    retry = 0
    
    while time.time() - start_time < timeout:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            'task_id': task_id,
            'retry_index': retry
        }
        
        resp = requests.get(url, params=params, headers=headers)
        data = resp.json()
        
        if data.get('code') != 0:
            print(f"❌ 轮询API返回错误: {data}")
            raise Exception(f"查询任务失败: {data.get('message')}")
        
        status = data['data']['status']
        print(f"⏳ 任务状态: {status} (重试: {retry})")
        
        if status == 2:  # 完成
            print("✅ 任务完成！")
            return data['data']
        elif status in [0, 1]:  # 进行中
            time.sleep(0.5)
            retry += 1
        else:  # 其他状态
            raise Exception(f"任务失败: {data['data'].get('message', '未知错误')}")
        
        retry += 1
        time.sleep(0.5)
    
    raise Exception("任务超时")


def get_target_fid_via_openlist(target_path: str) -> str:
    """通过OpenList原生API获取目标文件夹ID（不存在则创建）"""
    OPENLIST_URL = 'http://10.10.10.17:5255'
    OPENLIST_TOKEN = 'openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4'
    
    # 构建完整路径（夸克挂载在 /kuake）
    full_path = f"/kuake{target_path}"
    
    print(f"   完整路径: {full_path}")
    
    # 逐层检查和创建目录
    parts = [p for p in full_path.split('/') if p]
    current_path = ""
    
    for idx, part in enumerate(parts, 1):
        current_path = f"{current_path}/{part}"
        parent_path = "/".join(current_path.split('/')[:-1]) or "/"
        
        print(f"   第{idx}层: 检查 '{part}' 在 {parent_path}")
        
        # 列出父目录
        list_url = f"{OPENLIST_URL}/api/fs/list"
        headers = {"Authorization": OPENLIST_TOKEN, "Content-Type": "application/json"}
        body = {"path": parent_path, "refresh": False, "page": 1, "per_page": 1000}
        
        resp = requests.post(list_url, json=body, headers=headers)
        result = resp.json()
        
        if result.get('code') != 200:
            raise Exception(f"列出目录失败: {result.get('message')}")
        
        # 处理content可能为None的情况
        content = result.get('data', {}).get('content') or []
        
        # 查找目标文件夹
        found = False
        folder_id = None
        
        for item in content:
            is_mount = item.get('mount_details') is not None
            is_directory = item.get('is_dir') == True
            item_name = item.get('name', '').strip()
            
            if item_name == part.strip() and (is_directory or is_mount):
                folder_id = item.get('id', '')
                found = True
                print(f"      ✅ 找到: {part}, id={folder_id}")
                break
        
        # 不存在则创建
        if not found:
            print(f"      ❌ 未找到，创建: {part}")
            mkdir_path = f"{parent_path}/{part}" if parent_path != "/" else f"/{part}"
            mkdir_url = f"{OPENLIST_URL}/api/fs/mkdir"
            mkdir_body = {"path": mkdir_path}
            
            mkdir_resp = requests.post(mkdir_url, json=mkdir_body, headers=headers)
            mkdir_result = mkdir_resp.json()
            
            if mkdir_result.get('code') != 200:
                raise Exception(f"创建目录失败: {mkdir_result.get('message')}")
            
            # 重新列出，获取新建目录的ID
            resp = requests.post(list_url, json=body, headers=headers)
            result = resp.json()
            content = result.get('data', {}).get('content') or []
            
            for item in content:
                if item.get('name', '').strip() == part.strip() and item.get('is_dir'):
                    folder_id = item.get('id', '')
                    print(f"      ✅ 创建成功，id={folder_id}")
                    break
            
            if not folder_id:
                raise Exception(f"创建目录后无法获取ID: {part}")
    
    print(f"   ✅ 最终文件夹ID: {folder_id}")
    return folder_id


# ==================== 主测试流程 ====================

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              夸克智能转存测试                                  ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # 使用默认测试参数（你可以修改这里）
    # 📌 请提供一个有效的夸克分享链接！
    share_url = "https://pan.quark.cn/s/a68845606eba#/list/share/336d2f3a165142a9ae1539b2a29f11bf"  # 测试子文件夹的广告过滤
    target_path = "/A-闲鱼影视（自动更新）/测试/夸克智能转存测试"  # OpenList已修复，可以自动创建
    auto_select_clean = False  # 改为False，启用交互式选择
    
    # 📌 可以直接提供Cookie字符串（优先使用）
    USE_DIRECT_COOKIE = True  # 改为False则从数据库读取
    # 使用完整的Cookie JSON（包含httpOnly）
    DIRECT_COOKIE_JSON = [{"domain": ".quark.cn", "expirationDate": 1766913969, "hostOnly": False, "httpOnly": False, "name": "xlly_s", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "1"}, {"domain": ".quark.cn", "expirationDate": 1798436121.607245, "hostOnly": False, "httpOnly": False, "name": "b-user-id", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "1ebd53c9-25ba-a41e-3bb4-fc2b6de41441"}, {"domain": ".quark.cn", "expirationDate": 1769246770.381443, "hostOnly": False, "httpOnly": False, "name": "__sdid", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "AASm5h3PnZYoUs4XO/CuIHgM7ou7I4gfp8CUwiNCzVx4fy2g2cJYgEg3LcrfuRFjKS4="}, {"domain": ".quark.cn", "expirationDate": 1767262236.945407, "hostOnly": False, "httpOnly": True, "name": "_UP_D_", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "pc"}, {"domain": ".quark.cn", "expirationDate": 1798190772.282853, "hostOnly": False, "httpOnly": True, "name": "_UP_A4A_11_", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "wb9d01654e644b5ca4e5ac3cd38931d5"}, {"domain": ".quark.cn", "expirationDate": 1767867042.467939, "hostOnly": False, "httpOnly": True, "name": "__pus", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "fa70f96f32227a1366ded57572b73c71AAQZlNGCtfVRe5tK+rdQdlO1wGNjpbBS7lebnlQ0C4RR4GJ1SdyT7+ZR5ApPBPjglJw967mYoTMJdOFdwuDfM7pS"}, {"domain": ".quark.cn", "expirationDate": 1767867042.467985, "hostOnly": False, "httpOnly": False, "name": "__kp", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "f86c39a0-e179-11f0-8efa-a7f8cdf8b5d9"}, {"domain": ".quark.cn", "expirationDate": 1767867042.468003, "hostOnly": False, "httpOnly": False, "name": "__kps", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "AASN593sgdaQrTW/48UVrnOD"}, {"domain": ".quark.cn", "expirationDate": 1767867042.468014, "hostOnly": False, "httpOnly": False, "name": "__ktd", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "r4AuCjAEcKjUxTlg5xJB1A=="}, {"domain": ".quark.cn", "expirationDate": 1767867042.468032, "hostOnly": False, "httpOnly": False, "name": "__uid", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "AASN593sgdaQrTW/48UVrnOD"}, {"domain": ".quark.cn", "expirationDate": 1782452121, "hostOnly": False, "httpOnly": False, "name": "isg", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "BODgR4xYnXPUriFqCdCLmLzuseiy6cSzNeMY9Frx7PuOVYJ_AvguQ0dt6f1VZXyL"}, {"domain": ".quark.cn", "expirationDate": 1782452121, "hostOnly": False, "httpOnly": False, "name": "tfstk", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "gTzjkVq2XRUPw85ABK5yFtcTes36C_7FWCGTt5L26q3Y6VwSUj-VmcW_VRerHEuxWVg8LRfDMsjMwQhqIx3a0xlTF5eAif5mkYH_Cj1g7AhTwVGULFhOind0qJPpurSm7FgmSVBFLw7FmS0iWKwdIivmwXcN7fHtDq0JKQdl2w7UiSdqM6PR8oPrxchtBVnxX3F-EjdxWFLONYhsthpYBVC5NfG6XA3t673-6f3tBR3ON7Ho6VhYBVC7wYcts2AI1iM0G6WMx57NLiFoFFLTPbBipSw-ZbaSGmMK2YTT6zGjcvFbJa_zwfZLRm2dUnkYAk2IT-7JlJNYhknLkLBSS7rQCXaA9HM_n7Uq2rCwxb0gDk3Y599YZ-w0okFAU3G72SzS4yBB5mq8nkm_7T7nukPUSDUAlpDrxfwIku6JlJIPuekI31t6NDYsNv55NhxgocG7dSkGQ8ixZjiPN_9YjpY98FaNNhprDbcjZ_1WHlf.."}, {"domain": ".quark.cn", "expirationDate": 1766986644.604087, "hostOnly": False, "httpOnly": False, "name": "__puus", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "0489af49daf229b17f794c32cbd92f0dAAT1PrfXNhk3Gxfuk1rMWgk8GNeHkEprJxjctnSLhLx0ZIZbqLwlH/+sjmichgUCD4CEF8BLDMxkqTSZg0b1GNlj90kS/HMVUuNnmCNREa6+SqgGT9Day2JTxTyQBuzf8F2lqB4YuZoe1SZoLeVaL2ozGTN4qlrjV6GySmb8XFmpzggidnxtiEyfABI8pqujAI6xTtLtDt4hny/3byK+IjGx"}, {"domain": "pan.quark.cn", "expirationDate": 1798190769, "hostOnly": True, "httpOnly": False, "name": "b-user-id", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "1ebd53c9-25ba-a41e-3bb4-fc2b6de41441"}, {"domain": "pan.quark.cn", "expirationDate": 1782305818.066362, "hostOnly": True, "httpOnly": False, "name": "__wpkreporterwid_", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": "2486c771-fb87-4776-0539-d495829e05e0"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": False, "name": "ctoken", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "KDTxKEYxfU5Qx0znaKi3uKvd"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": True, "name": "web-grey-id", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "9d5b08d9-3097-e30a-8f1f-c1aa8789c1db"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": True, "name": "web-grey-id.sig", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "TOx_KIs-EkczpdJ3ZxLui4Z21w0VlpH-vkMxpmrQIvg"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": True, "name": "grey-id", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "f4c63a5b-0f73-5ae1-c554-a4be6c624fb4"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": True, "name": "grey-id.sig", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "I-w9_sCEai-wJL8cKwZ0Dc_Thus65wb2jurcckcNQTM"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": True, "name": "isQuark", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "true"}, {"domain": "pan.quark.cn", "hostOnly": True, "httpOnly": True, "name": "isQuark.sig", "path": "/", "sameSite": "unspecified", "secure": False, "session": True, "storeId": "0", "value": "hUgqObykqFom5Y09bll94T1sS9abT1X-4Df_lzgl8nM"}, {"domain": ".pan.quark.cn", "expirationDate": 1766986522.057229, "hostOnly": False, "httpOnly": False, "name": "__chkey", "path": "/", "sameSite": "unspecified", "secure": False, "session": False, "storeId": "0", "value": ""}]
    
    print(f"📋 测试配置:")
    print(f"   分享链接: {share_url}")
    print(f"   目标路径: {target_path}")
    print(f"   自动模式: {'是（自动转存所有干净文件）' if auto_select_clean else '否（仅显示列表）'}")
    print(f"   Cookie来源: {'直接提供' if USE_DIRECT_COOKIE else '数据库'}")
    print()
    
    print("\n" + "="*60)
    print("步骤1: 获取Cookie")
    print("="*60)
    
    if USE_DIRECT_COOKIE:
        cookie = convert_cookie_json_to_string(DIRECT_COOKIE_JSON)
        print(f"✅ 使用直接提供的Cookie (长度: {len(cookie)})")
    else:
        # 从数据库获取
        engine = init_database()
        session = get_session(engine)
        
        cookie_obj = session.query(PanCookie).filter(
            PanCookie.pan_type == 'quark',
            PanCookie.is_active == True
        ).first()
        
        if not cookie_obj:
            print("❌ 未找到夸克Cookie，请先配置")
            return
        
        # 转换Cookie格式（支持JSON和字符串）
        cookie = convert_cookie_json_to_string(cookie_obj.cookie)
        print(f"✅ 从数据库获取Cookie成功 (长度: {len(cookie)})")
    
    print(f"   Cookie前50字符: {cookie[:50]}...")
    
    # 步骤2: 解析URL
    print("\n" + "="*60)
    print("步骤2: 解析分享URL")
    print("="*60)
    
    pwd_id, pdir_fid = parse_share_url(share_url)
    print(f"✅ pwd_id: {pwd_id}")
    print(f"✅ pdir_fid: {pdir_fid}")
    
    # 步骤3: 获取stoken
    print("\n" + "="*60)
    print("步骤3: 获取stoken")
    print("="*60)
    
    stoken = get_stoken(cookie, pwd_id)
    
    # 步骤4: 获取文件列表
    print("\n" + "="*60)
    print("步骤4: 获取文件列表")
    print("="*60)
    
    share_info = get_quark_file_list(cookie, pwd_id, stoken, pdir_fid)
    all_files = share_info['files']
    
    print(f"✅ 获取文件列表成功")
    print(f"   文件总数: {len(all_files)}")
    
    # 步骤4: 过滤广告并显示文件列表
    print("\n" + "="*60)
    print("步骤4: 文件列表（含广告标注）")
    print("="*60)
    
    ad_files = []
    clean_files = []
    
    print(f"\n{'序号':<4} {'类型':<6} {'文件名':<50} {'大小':<12}")
    print("-" * 80)
    
    for idx, file in enumerate(all_files, 1):
        is_ad = is_ad_file(file['file_name'], file['size'])
        size_mb = file['size'] / 1024 / 1024
        
        if is_ad:
            ad_files.append(file)
            ad_mark = "🚫广告"
        else:
            clean_files.append(file)
            ad_mark = "✅正常"
        
        print(f"{idx:<4} {ad_mark:<6} {file['file_name']:<50} {size_mb:>10.2f}MB")
    
    print(f"\n📊 统计:")
    print(f"   总文件: {len(all_files)}")
    print(f"   广告文件: {len(ad_files)}")
    print(f"   干净文件: {len(clean_files)}")
    
    # 根据配置选择模式
    print("\n" + "="*60)
    print("步骤5: 选择要转存的文件")
    print("="*60)
    
    if auto_select_clean:
        # 自动模式：转存所有干净文件
        to_transfer = clean_files
        print(f"✅ 自动模式：将转存所有干净文件 ({len(to_transfer)} 个)")
    else:
        # 交互模式：让用户选择
        print("💡 交互模式：请选择要转存的文件")
        print("\n📝 输入说明：")
        print("  - 直接输入 'all' 或 'a' = 转存所有干净文件（过滤广告）")
        print("  - 输入序号范围 = 手动选择文件")
        print("    支持格式：1,3,5  或  1-5  或  1,3-5,7  或  4-16")
        print("  - 输入 'exit' 或 'q' = 仅显示列表，不转存")
        
        choice = input("\n请输入 (all/序号/exit): ").strip().lower()
        
        if choice in ['exit', 'q', '']:
            print("ℹ️  操作已取消")
            return
        elif choice in ['all', 'a']:
            # 过滤掉文件夹（只转存真正的文件）
            to_transfer = []
            skipped_folders = []
            for file in clean_files:
                # 判断是否为文件夹：file字段为False 或 dir字段为True
                is_folder = file.get('file', True) == False or file.get('dir', False)
                if is_folder:
                    skipped_folders.append(file['file_name'])
                else:
                    to_transfer.append(file)
            
            if skipped_folders:
                print(f"\n⚠️  已自动跳过 {len(skipped_folders)} 个文件夹：")
                for name in skipped_folders:
                    print(f"     - {name}")
            
            print(f"\n✅ 将转存 {len(to_transfer)} 个文件")
        else:
            # 解析为序号
            indices_str = choice
            
            try:
                # 解析序号
                selected_indices = set()
                for part in indices_str.split(','):
                    part = part.strip()
                    if '-' in part:
                        # 范围：1-5
                        start, end = part.split('-')
                        selected_indices.update(range(int(start), int(end) + 1))
                    else:
                        # 单个：3
                        selected_indices.add(int(part))
                
                # 选择文件（跳过广告和文件夹）
                to_transfer = []
                skipped_ads = []
                skipped_folders = []
                
                for idx in sorted(selected_indices):
                    if 1 <= idx <= len(all_files):
                        file = all_files[idx - 1]
                        
                        # 跳过广告
                        if is_ad_file(file['file_name'], file['size']):
                            skipped_ads.append(file['file_name'])
                            continue
                        
                        # 跳过文件夹
                        if file.get('file', False) == False or file.get('dir', False):
                            skipped_folders.append(file['file_name'])
                            continue
                        
                        to_transfer.append(file)
                
                if skipped_ads:
                    print(f"\n⚠️  已自动跳过 {len(skipped_ads)} 个广告文件：")
                    for name in skipped_ads[:5]:  # 只显示前5个
                        print(f"     - {name}")
                    if len(skipped_ads) > 5:
                        print(f"     ... 还有 {len(skipped_ads) - 5} 个")
                
                if skipped_folders:
                    print(f"\n⚠️  已自动跳过 {len(skipped_folders)} 个文件夹（暂不支持文件夹转存）：")
                    for name in skipped_folders:
                        print(f"     - {name}")
                
                if not to_transfer:
                    print("❌ 没有可转存的文件")
                    return
                
                print(f"\n✅ 将转存 {len(to_transfer)} 个文件")
                
            except Exception as e:
                print(f"❌ 输入格式错误: {e}")
                return
    
    # 步骤6: 获取目标文件夹ID
    print("\n" + "="*60)
    print("步骤6: 获取目标文件夹ID")
    print("="*60)
    
    # 测试模式：可以直接指定fid跳过OpenList
    USE_DIRECT_FID = False  # 改为True跳过OpenList，用根目录测试完整流程
    DIRECT_FID = "0"  # 直接使用根目录测试
    
    if USE_DIRECT_FID:
        target_fid = DIRECT_FID
        print(f"✅ 使用直接指定的FID: {target_fid}")
    else:
        try:
            target_fid = get_target_fid_via_openlist(target_path)
        except Exception as e:
            print(f"❌ OpenList失败: {e}")
            print("💡 提示：可以设置 USE_DIRECT_FID=True 使用根目录(0)测试")
            return
    print(f"✅ 目标文件夹ID: {target_fid}")
    
    # 步骤7: 智能选择策略
    print("\n" + "="*60)
    print("步骤7: 智能选择策略")
    print("="*60)
    
    ratio = len(to_transfer) / len(all_files)
    print(f"选择比例: {ratio*100:.1f}%")
    
    if ratio == 1:
        mode = "全选模式"
        params = {
            'pdir_save_all': True
        }
    elif ratio > 0.5:
        mode = "排除模式"
        exclude_fids = [f['fid'] for f in all_files if f not in to_transfer]
        params = {
            'pdir_save_all': True,
            'exclude_fids': exclude_fids
        }
    else:
        mode = "包含模式"
        params = {
            'pdir_save_all': False,  # ❗包含模式必须是False
            'fid_list': [f['fid'] for f in to_transfer],
            'fid_token_list': [f['share_fid_token'] for f in to_transfer]
        }
    
    print(f"✅ 使用策略: {mode}")
    
    # 自动确认转存
    print("\n" + "="*60)
    print("准备转存")
    print("="*60)
    print(f"分享链接: {share_url}")
    print(f"目标路径: {target_path}")
    print(f"转存文件: {len(to_transfer)} 个")
    print(f"转存策略: {mode}")
    print("\n⚠️  将在3秒后自动开始转存...")
    time.sleep(3)
    
    # 步骤8: 调用转存API
    print("\n" + "="*60)
    print("步骤8: 调用转存API")
    print("="*60)
    
    task_id = call_quark_transfer_api(
        cookie=cookie,
        stoken=stoken,
        pwd_id=pwd_id,
        pdir_fid=pdir_fid,
        to_pdir_fid=target_fid,
        **params
    )
    
    print(f"✅ 任务创建成功: {task_id}")
    
    # 步骤9: 轮询任务
    print("\n" + "="*60)
    print("步骤9: 轮询任务状态")
    print("="*60)
    
    result = poll_quark_task(cookie, task_id)
    
    print("\n" + "="*60)
    print("✅ 转存完成！")
    print("="*60)
    print(f"转存文件: {len(to_transfer)}")
    print(f"目标路径: {target_path}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

