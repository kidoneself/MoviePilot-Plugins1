#!/usr/bin/env python3
"""
测试转存API接口
"""
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000"

def test_get_status():
    """测试获取转存功能状态"""
    print("\n" + "="*60)
    print("测试：获取转存功能状态")
    print("="*60)
    
    url = f"{BASE_URL}/api/transfer/status"
    response = requests.get(url)
    
    print(f"状态码: {response.status_code}")
    print(f"响应:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_single_transfer():
    """测试单个转存"""
    print("\n" + "="*60)
    print("测试：单个文件转存")
    print("="*60)
    
    url = f"{BASE_URL}/api/transfer"
    data = {
        "share_url": "https://pan.baidu.com/s/1wNS_9HtA7QRhJmTLLNYfrQ?pwd=7848",
        "pass_code": "7848",
        "target_path": "/电影/测试/API测试文件",
        "pan_type": "baidu",
        "use_openlist": True
    }
    
    print(f"请求数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    
    response = requests.post(url, json=data)
    
    print(f"\n状态码: {response.status_code}")
    print(f"响应:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()


def test_batch_transfer():
    """测试批量转存"""
    print("\n" + "="*60)
    print("测试：批量转存（三网盘）")
    print("="*60)
    
    url = f"{BASE_URL}/api/transfer/batch"
    data = {
        "share_links": [
            {
                "share_url": "https://pan.baidu.com/s/1wNS_9HtA7QRhJmTLLNYfrQ?pwd=7848",
                "pass_code": "7848",
                "pan_type": "baidu"
            },
            {
                "share_url": "https://pan.quark.cn/s/2b6409aeb29c",
                "pass_code": None,
                "pan_type": "quark"
            },
            {
                "share_url": "https://pan.xunlei.com/s/VO82pmLAutykC42tz8pmf0Q9A1",
                "pass_code": None,
                "pan_type": "xunlei"
            }
        ],
        "target_path": "/电影/测试/批量转存测试",
        "use_openlist": True
    }
    
    print(f"请求数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    
    response = requests.post(url, json=data)
    
    print(f"\n状态码: {response.status_code}")
    result = response.json()
    print(f"响应:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 显示汇总
    if 'results' in result:
        print(f"\n汇总:")
        print(f"  总数: {result.get('total')}")
        print(f"  成功: {result.get('success_count')}")
        print(f"  失败: {result.get('failed_count')}")
        
        print(f"\n详细结果:")
        for r in result['results']:
            status = "✅" if r.get('success') else "❌"
            print(f"  {status} {r.get('pan_type')}: {r.get('message')}")
    
    return result


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              网盘转存API接口测试                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # 1. 测试状态接口
        status = test_get_status()
        
        # 2. 测试单个转存
        # single_result = test_single_transfer()
        
        # 3. 测试批量转存
        # batch_result = test_batch_transfer()
        
        print("\n" + "="*60)
        print("测试完成！")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到API服务")
        print("请确保后端服务已启动：")
        print("  cd backend && python main.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
