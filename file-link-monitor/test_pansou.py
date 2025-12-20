#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PanSou API 测试脚本
"""
import requests
import json

# PanSou API 配置
PANSOU_API_URL = "http://10.10.10.17:9978/api/search"  # PanSou API 地址
PANSOU_TOKEN = ""  # 如果启用了认证，填写token；否则留空

def test_pansou_search(keyword: str, cloud_types: list = None, plugins: list = None):
    """
    测试 PanSou 搜索 API
    
    Args:
        keyword: 搜索关键词
        cloud_types: 网盘类型列表，如 ['baidu', 'quark', 'xunlei']
        plugins: 插件列表
    """
    print(f"\n{'='*60}")
    print(f"🔍 搜索关键词: {keyword}")
    print(f"{'='*60}\n")
    
    # 构建请求参数
    payload = {
        "kw": keyword,
        "res": "merge",  # 返回按网盘类型分组的结果
        "src": "all"     # 全部数据源
    }
    
    # 可选参数
    if cloud_types:
        payload["cloud_types"] = cloud_types
        print(f"🗂️  网盘类型: {', '.join(cloud_types)}")
    
    if plugins:
        payload["plugins"] = plugins
        print(f"🔌 使用插件: {', '.join(plugins)}")
    
    # 请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    if PANSOU_TOKEN:
        headers["Authorization"] = f"Bearer {PANSOU_TOKEN}"
    
    try:
        print(f"\n📤 发送请求到: {PANSOU_API_URL}")
        print(f"📦 请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
        
        # 发送请求
        response = requests.post(
            PANSOU_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ 请求成功！\n")
            print(f"📈 总结果数: {data.get('total', 0)}")
            
            # 解析 merged_by_type
            merged = data.get('merged_by_type', {})
            
            if merged:
                print(f"\n🗂️  按网盘类型分组的结果:\n")
                
                for cloud_type, links in merged.items():
                    print(f"  📦 {cloud_type.upper()} ({len(links)} 条):")
                    
                    for idx, link in enumerate(links[:3], 1):  # 只显示前3条
                        print(f"    {idx}. {link.get('note', '无标题')}")
                        print(f"       🔗 URL: {link.get('url', 'N/A')}")
                        if link.get('password'):
                            print(f"       🔑 提取码: {link.get('password')}")
                        print(f"       📅 时间: {link.get('datetime', 'N/A')}")
                        print(f"       📌 来源: {link.get('source', 'N/A')}")
                        print()
                    
                    if len(links) > 3:
                        print(f"    ... 还有 {len(links) - 3} 条结果\n")
            else:
                print(f"\n⚠️  未找到匹配的网盘链接")
            
            # 保存完整结果到文件
            output_file = f"pansou_result_{keyword.replace(' ', '_')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n💾 完整结果已保存到: {output_file}")
            
            return data
            
        else:
            print(f"❌ 请求失败!")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时!")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print(f"响应内容: {response.text}")
        return None


def test_multiple_searches():
    """测试多个搜索案例"""
    
    test_cases = [
        {
            "keyword": "守护者联盟 2019",
            "cloud_types": ["baidu", "quark", "xunlei"],
            "description": "测试剧集搜索 - 指定三网盘"
        },
        {
            "keyword": "生化启示录 2025",
            "cloud_types": ["baidu"],
            "description": "测试电影搜索 - 仅百度盘"
        },
        {
            "keyword": "哑舍",
            "cloud_types": None,
            "description": "测试简短关键词 - 所有网盘"
        }
    ]
    
    results = []
    
    for idx, case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*60}")
        print(f"测试用例 {idx}/{len(test_cases)}: {case['description']}")
        print(f"{'#'*60}")
        
        result = test_pansou_search(
            keyword=case["keyword"],
            cloud_types=case["cloud_types"]
        )
        
        results.append({
            "case": case,
            "success": result is not None,
            "total": result.get('total', 0) if result else 0
        })
        
        # 等待一下，避免请求过快
        import time
        time.sleep(2)
    
    # 汇总报告
    print(f"\n\n{'='*60}")
    print(f"📊 测试汇总报告")
    print(f"{'='*60}\n")
    
    for idx, res in enumerate(results, 1):
        status = "✅ 成功" if res["success"] else "❌ 失败"
        print(f"{idx}. {res['case']['description']}")
        print(f"   关键词: {res['case']['keyword']}")
        print(f"   状态: {status}")
        print(f"   结果数: {res['total']}")
        print()


if __name__ == "__main__":
    print("🚀 PanSou API 测试脚本")
    print("=" * 60)
    
    # 检查配置
    if PANSOU_API_URL == "http://your-pansou-api-url/api/search":
        print("\n⚠️  请先修改 PANSOU_API_URL 为实际的 PanSou API 地址!")
        print("   例如: http://localhost:3000/api/search")
        exit(1)
    
    # 单个测试
    print("\n📝 单个测试示例:\n")
    test_pansou_search(
        keyword="守护者联盟 2019",
        cloud_types=["baidu", "quark", "xunlei"]
    )
    
    # 批量测试（可选）
    # test_multiple_searches()
