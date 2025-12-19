"""
测试迅雷网盘API - 验证搜索+创建分享链接逻辑
"""
import requests
import json
from urllib.parse import quote

# 从curl中提取的关键信息
AUTHORIZATION = "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjRjYWY3NDQ1LTgzMzItNDQ5ZS04MzMzLWFhMzc5NGMwZWU3YSJ9.eyJpc3MiOiJodHRwczovL3hsdXNlci1zc2wueHVubGVpLmNvbSIsInN1YiI6IjY4MzY3NjIxMyIsImF1ZCI6IlhxcDBrSkJYV2h3YVRwQjYiLCJleHAiOjE3NjYxODg2MzEsImlhdCI6MTc2NjE0NTQzMSwiYXRfaGFzaCI6InIubVRWU3RValBSUzZXeTlUdzNLX0xaQSIsInNjb3BlIjoicHJvZmlsZSBwYW4gc3NvIHVzZXIiLCJwcm9qZWN0X2lkIjoiMnJ2azRlM2drZG5sN3Uxa2wwayIsIm1ldGEiOnsiYSI6ImFiV1djQnBMR1hBVkZ3WnlnYTJEY3BzdHpGV2dlNCtqSzhvRFFQWTlrdlk9In19.dbLHUF6i3g4IiQ9pql1YssKLpcRB9Os0QaHAd4k6TxFd3MA0RLyIkF-TusRn1uFi-0BuwiY0XPSqByV7cPOW8ZrDIFaK5UdMo69iFVC0TMRVqQTzVTZHuz1ETXFGG-btNbB7Lo4W6Zt6a4CsdIGafNnzVy4GZONjFxeCWkhSoSROYaCOyZPKsGc_zuNh02AlaPAiv_8j5g-vzxMoeijnaYNeZ1QNebTveJaWs93XY25E4GM6MQJQqqWEvduuTKHgsLTafSYJKVSeZKSwOWNJLyrYKpWpu63w-apCUt2fJzEnJ4mMhBKztJTwMuamiqwexO--0Zr1lYnfF94JhvogeA"
X_CAPTCHA_TOKEN = "ck0.syGPjelgnsnoe2JzDt_3duqmaqdTAlggEIPChbqPWUL0rJ71L0k7350uR2P1Dz2SdCNjjqLlo9eFhYPDAWBP4GfPD-zC4bOFwQf3kJfG7DRBBu-w3-yuFUFd-1hhpxEyIqanCtjbnMM83zG6DLrs5WZEKrVg0Pty_weqOCOxz703q-zwcoIq3WW-ADy6ZtzVll_HwXih4W2BFF_llTevaR1nrBvRlys91vsMKMT-mwPAy0gXfEs-7xuKClW9lRYra1LJRWmWFLjw1cJs2BiJ2Rq4bLKkef8TuLBFqf0cAuInzDxXKBMf4SxusORP_3ZosWrY07TslrGP4aMNAd60OoJwzhB_-Ai4lJUiRBx9PxqlnipdaCs8oR8VbbJhCgiq3pfCT0wppjoFz3ab-RnotC6xytSn7llkgHciZw5qG7-CJJrubWkN_oKCKBsiPTR1C5ixSd833OfU1fpmlPY6OQ.ClQIhbedtbMzEhBYcXAwa0pCWFdod2FUcEI2GgcxLjkyLjIxIg5wYW4ueHVubGVpLmNvbSogZDc2NWE0OTEyNGQwYjRjOGQ1OTNkNzNkYWE3MzhmNTESgAENuoRIlZBhuCqWCk8tOXTJk6fI8PbMbr3DpE-DETKIfd3QuGRG-19fiEFeKDgaB7oHilLkzPKfUJonHS7a6CQqaMdBayXN5-bT2BSkr1ip-i5U4UTuvMZh5hdvqtqoEl1WSlonad9y8Ayyj0Z7TO0-AF-zSG2T4YuqTS6zyzTb1w"
X_CLIENT_ID = "Xqp0kJBXWhwaTpB6"
X_DEVICE_ID = "d765a49124d0b4c8d593d73daa738f51"
USER_ID = "683676213"

def get_headers():
    """构造请求头"""
    return {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
        'authorization': AUTHORIZATION,
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://pan.xunlei.com',
        'pragma': 'no-cache',
        'referer': 'https://pan.xunlei.com/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-captcha-token': X_CAPTCHA_TOKEN,
        'x-client-id': X_CLIENT_ID,
        'x-device-id': X_DEVICE_ID
    }

def search_file(filename):
    """搜索文件获取file_id"""
    url = "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search"
    
    params = {
        'keyword': filename,
        'limit': 20,
        'space': '*',
        'user_id': USER_ID,
        'parent_id': '',
        'page_token': ''
    }
    
    headers = get_headers()
    
    print(f"🔍 搜索文件: {filename}")
    response = requests.get(url, params=params, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    data = response.json()
    print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    if data.get('code') != 0:
        raise Exception(f"搜索失败: code={data.get('code')}, message={data.get('message')}")
    
    files = data.get('data', {}).get('files', [])
    if not files:
        raise Exception(f"未找到文件: {filename}")
    
    # 精确匹配文件夹
    for item in files:
        if item['name'] == filename and item.get('kind') == 'drive#folder':
            print(f"✅ 找到文件夹: {item['name']}")
            print(f"   file_id: {item['id']}")
            print(f"   user_id: {item['user_id']}")
            return item['id']
    
    # 如果没有精确匹配，返回第一个结果
    first_item = files[0]
    print(f"✅ 找到文件: {first_item['name']}")
    print(f"   file_id: {first_item['id']}")
    return first_item['id']

def create_share_link(file_id, title="云盘资源分享"):
    """创建分享链接"""
    url = "https://api-pan.xunlei.com/drive/v1/share"
    
    payload = {
        "file_ids": [file_id],
        "share_to": "copy",
        "params": {
            "subscribe_push": "false",
            "WithPassCodeInLink": "true"
        },
        "title": title,
        "restore_limit": "-1",
        "expiration_days": "-1"  # -1表示永久
    }
    
    headers = get_headers()
    
    print(f"📤 创建分享链接...")
    print(f"   file_id: {file_id}")
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    result = response.json()
    print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if 'share_url' not in result:
        raise Exception(f"创建分享链接失败: {result}")
    
    share_url = result['share_url']
    pass_code = result.get('pass_code', '')
    
    print(f"✅ 分享链接创建成功!")
    print(f"   链接: {share_url}")
    print(f"   提取码: {pass_code}")
    
    return f"{share_url}?pwd={pass_code} 提取码: {pass_code}"

def main():
    """主测试流程"""
    print("=" * 60)
    print("迅雷网盘API测试")
    print("=" * 60)
    
    # 测试文件名（从curl例子中提取）
    test_filename = "A-闲鱼影视（自动更新）"
    
    try:
        # 1. 搜索文件获取file_id
        print("\n" + "=" * 60)
        file_id = search_file(test_filename)
        
        # 2. 创建分享链接
        print("\n" + "=" * 60)
        share_link = create_share_link(file_id)
        
        # 3. 输出结果
        print("\n" + "=" * 60)
        print("🎉 测试成功!")
        print(f"完整分享链接: {share_link}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
