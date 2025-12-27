"""
测试用户资源请求API
"""
import requests
import json

BASE_URL = "http://localhost:8080/api"

def test_create_request():
    """测试创建资源请求"""
    print("=" * 50)
    print("测试创建资源请求")
    print("=" * 50)
    
    data = {
        "tmdb_id": 1381967,
        "media_type": "movie",
        "title": "流浪地球：飞跃2020特别版",
        "year": "2020",
        "poster_url": "https://image.tmdb.org/t/p/w300/kzRs3qB2Hd6gPmL8NKSHFs8E8CK.jpg"
    }
    
    response = requests.post(f"{BASE_URL}/media-requests", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    print()


def test_get_requests():
    """测试获取请求列表"""
    print("=" * 50)
    print("测试获取请求列表")
    print("=" * 50)
    
    params = {
        "status": "pending",
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/media-requests", params=params)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"成功: {result.get('success')}")
    print(f"总数: {result.get('total')}")
    print(f"待处理: {result.get('pending_count')}")
    print(f"数据条数: {len(result.get('data', []))}")
    
    if result.get('data'):
        print("\n前3条数据:")
        for i, item in enumerate(result['data'][:3], 1):
            print(f"  {i}. {item['title']} ({item['year']}) - 请求{item['request_count']}次")
    print()


def test_update_request():
    """测试更新请求状态"""
    print("=" * 50)
    print("测试更新请求状态")
    print("=" * 50)
    
    # 先获取一个请求
    response = requests.get(f"{BASE_URL}/media-requests", params={"page": 1, "page_size": 1})
    data = response.json().get('data', [])
    
    if not data:
        print("没有可更新的请求")
        return
    
    request_id = data[0]['id']
    print(f"更新请求ID: {request_id}")
    
    update_data = {
        "status": "completed"
    }
    
    response = requests.put(f"{BASE_URL}/media-requests/{request_id}", json=update_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    print()


def test_get_stats():
    """测试获取统计信息"""
    print("=" * 50)
    print("测试获取统计信息")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/media-requests/stats")
    print(f"状态码: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        stats = result['data']
        print(f"总请求数: {stats['total']}")
        print(f"待处理: {stats['pending']}")
        print(f"已完成: {stats['completed']}")
        
        if stats['hot_requests']:
            print("\n热门请求TOP 5:")
            for i, req in enumerate(stats['hot_requests'][:5], 1):
                print(f"  {i}. {req['title']} - {req['request_count']}次")
    print()


def test_delete_request():
    """测试删除请求"""
    print("=" * 50)
    print("测试删除请求（仅演示，不实际执行）")
    print("=" * 50)
    print("如需删除，请手动调用:")
    print("  requests.delete(f'{BASE_URL}/media-requests/{request_id}')")
    print()


if __name__ == "__main__":
    print("\n🧪 开始测试用户资源请求API\n")
    
    try:
        # 1. 测试创建请求
        test_create_request()
        
        # 2. 测试获取列表
        test_get_requests()
        
        # 3. 测试获取统计
        test_get_stats()
        
        # 4. 测试更新状态（可选）
        # test_update_request()
        
        # 5. 删除测试（仅说明）
        test_delete_request()
        
        print("✅ 测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保后端服务正在运行（http://localhost:8080）")
    except Exception as e:
        print(f"❌ 测试出错: {e}")

