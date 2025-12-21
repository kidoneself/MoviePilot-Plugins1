#!/usr/bin/env python3
"""
测试夸克转存：达升益仁
"""
import sys
import os
import yaml
import requests
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.models import init_database, get_session, PanCookie
from pan_transfer_api import PanTransferAPI

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              夸克转存测试 - 达升益仁                           ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # 配置
    share_url = "https://pan.quark.cn/s/bea15160983d"
    target_path = "/A-闲鱼影视（自动更新）/剧集/国产剧集/达升益仁"
    pan_type = "quark"
    
    print(f"分享链接: {share_url}")
    print(f"目标路径: {target_path}")
    print(f"网盘类型: {pan_type}")
    print()
    
    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 初始化数据库
    engine = init_database()
    db_session = get_session(engine)
    
    # 检查认证信息
    print("⚠️  正在检查夸克认证信息...")
    pan_record = db_session.query(PanCookie).filter_by(
        pan_type='quark',
        is_active=True
    ).first()
    
    if not pan_record:
        print("❌ 未找到夸克认证信息")
        return
    
    print("✅ 认证信息已加载")
    print()
    
    # 获取文件夹ID
    print("="*60)
    print("步骤1: 获取文件夹ID")
    print("="*60)
    
    openlist_url = "http://10.10.10.17:5255"
    openlist_token = "openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4"
    
    # OpenList路径需要加网盘前缀
    openlist_path = f"/kuake{target_path}"
    print(f"OpenList路径: {openlist_path}")
    
    try:
        # 获取文件夹信息
        headers = {
            'Authorization': openlist_token,
            'Content-Type': 'application/json'
        }
        response = requests.post(
            f"{openlist_url}/api/fs/get",
            json={"path": openlist_path},
            headers=headers
        )
        result_data = response.json()
        
        if result_data.get('code') != 200:
            print(f"❌ 获取文件夹信息失败: {result_data.get('message')}")
            return
        
        # 夸克文件夹ID在 'id' 字段
        folder_id = result_data['data'].get('id')
        print(f"✅ 文件夹ID: {folder_id}")
        print(f"   文件夹名: {result_data['data'].get('name')}")
        print()
        
    except Exception as e:
        print(f"❌ 获取文件夹ID失败: {e}")
        return
    
    # 使用PanTransferAPI转存
    print("="*60)
    print("步骤2: 开始转存...")
    print("="*60)
    
    try:
        # 创建API实例
        api = PanTransferAPI(pan_type='quark', credentials={'cookie': pan_record.cookie})
        
        # 转存（夸克需要文件夹ID）
        result = api.transfer(
            share_url=share_url,
            pass_code=None,
            target_path=folder_id
        )
        
        print()
        if result['success']:
            print("✅ 转存成功！")
            print(f"   文件数量: {result['file_count']}")
            print(f"   文件ID: {result['file_ids']}")
            print(f"   消息: {result['message']}")
            if result.get('details'):
                print(f"   详情: {result['details']}")
        else:
            print("❌ 转存失败")
            print(f"   消息: {result['message']}")
        
        print()
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 转存异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()


if __name__ == "__main__":
    main()
