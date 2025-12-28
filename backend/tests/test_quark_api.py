#!/usr/bin/env python3
"""
测试夸克智能转存API

使用方法：
1. 确保后端服务运行在 http://10.10.10.17:9889
2. 运行此脚本：python3 test_quark_api.py
"""

import requests
import json
import time

API_BASE = "http://10.10.10.17:9889/api"

# 测试数据
SHARE_URL = "https://pan.quark.cn/s/a68845606eba#/list/share/336d2f3a165142a9ae1539b2a29f11bf"
MEDIA_NAME = "测试剧"  # 请在数据库中配置这个映射


def print_step(step, title):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤{step}: {title}")
    print('='*60)


def test_full_flow():
    """测试完整流程"""
    
    # 步骤1: 解析分享链接
    print_step(1, "解析分享链接")
    resp = requests.post(f"{API_BASE}/quark/parse-share", json={
        "share_url": SHARE_URL
    })
    
    print(f"状态码: {resp.status_code}")
    data = resp.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    if not data.get('success'):
        print("❌ 解析失败")
        return
    
    session_id = data['session_id']
    files = data['files']
    stats = data['stats']
    
    print(f"✅ 解析成功")
    print(f"   会话ID: {session_id}")
    print(f"   文件总数: {stats['total']}")
    print(f"   广告文件: {stats['ad_count']}")
    print(f"   干净文件: {stats['clean_count']}")
    
    # 显示前5个文件
    print(f"\n前5个文件：")
    for file in files[:5]:
        mark = "🚫" if file['is_ad'] else "✅"
        print(f"   {mark} {file['index']}. {file['name']} ({file['size'] / 1024 / 1024:.2f}MB)")
    
    # 步骤2: 选择文件
    print_step(2, "选择文件")
    
    # 选择所有干净文件
    selection = input("\n请输入选择 (all/序号，如 1,3,5-10，直接回车默认all): ").strip() or "all"
    
    resp = requests.post(f"{API_BASE}/quark/select-files", json={
        "session_id": session_id,
        "selection": selection
    })
    
    data = resp.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    if not data.get('success'):
        print("❌ 选择失败")
        return
    
    print(f"✅ 已选择 {data['selected_count']} 个文件")
    if data.get('skipped_ads'):
        print(f"   跳过广告: {len(data['skipped_ads'])} 个")
    
    # 步骤3: 输入剧名查询路径
    print_step(3, "查询目标路径")
    
    media_name = input(f"\n请输入剧名 (直接回车默认'{MEDIA_NAME}'): ").strip() or MEDIA_NAME
    
    resp = requests.post(f"{API_BASE}/quark/get-target-path", json={
        "session_id": session_id,
        "media_name": media_name
    })
    
    data = resp.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    if not data.get('success'):
        print(f"❌ {data.get('error')}: {data.get('message')}")
        return
    
    print(f"✅ 找到目标路径")
    print(f"   显示路径: {data['display_path']}")
    print(f"   完整路径: {data['full_path']}")
    print(f"\n{data['message']}")
    
    # 步骤4: 确认并执行转存
    confirm = input("\n确认转存? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 用户取消")
        return
    
    print_step(4, "执行转存")
    
    resp = requests.post(f"{API_BASE}/quark/execute-transfer", json={
        "session_id": session_id
    })
    
    data = resp.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    if not data.get('success'):
        print("❌ 转存失败")
        return
    
    task_id = data['task_id']
    print(f"✅ 任务创建成功")
    print(f"   任务ID: {task_id}")
    print(f"   策略: {data['mode']}")
    
    # 步骤5: 轮询任务状态
    print_step(5, "查询任务状态")
    
    max_retries = 30
    for i in range(max_retries):
        print(f"\r⏳ 轮询中... ({i+1}/{max_retries})", end='', flush=True)
        
        resp = requests.get(f"{API_BASE}/quark/task-status/{task_id}")
        data = resp.json()
        
        if data.get('status') == 'completed':
            print(f"\n\n✅ 转存完成！")
            print(f"   {data['message']}")
            break
        elif data.get('status') == 'processing':
            time.sleep(2)
        else:
            print(f"\n❌ 转存失败: {data}")
            break
    else:
        print(f"\n⚠️ 超时，但任务可能仍在进行")


def test_list_media_names():
    """测试获取剧名列表"""
    print_step(0, "获取可用剧名列表")
    
    resp = requests.get(f"{API_BASE}/quark/list-media-names")
    data = resp.json()
    
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    if data.get('success'):
        print(f"✅ 共有 {data['total']} 个剧名")
        print(f"   前10个: {data['media_names'][:10]}")


if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              夸克智能转存API测试                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"API地址: {API_BASE}")
    print(f"测试链接: {SHARE_URL}")
    print(f"默认剧名: {MEDIA_NAME}")
    
    # 先测试剧名列表
    test_list_media_names()
    
    # 测试完整流程
    input("\n\n按回车开始测试完整流程...")
    test_full_flow()

