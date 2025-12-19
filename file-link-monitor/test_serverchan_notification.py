#!/usr/bin/env python3
"""
ServerChan通知测试脚本

测试TaoSync触发时是否会发送ServerChan通知
"""

import sys
import yaml
import logging
from pathlib import Path

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.utils.taosync import TaoSyncClient
from backend.utils.notifier import Notifier

def test_serverchan():
    """测试ServerChan通知"""
    print("=" * 60)
    print("ServerChan通知测试")
    print("=" * 60)
    
    # 加载配置
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 显示配置信息
    notification_config = config.get('notification', {})
    taosync_config = config.get('taosync', {})
    
    print(f"\n通知配置：")
    print(f"  启用: {notification_config.get('enabled')}")
    print(f"  URL: {notification_config.get('serverchan_url')[:50]}..." if notification_config.get('serverchan_url') else "  URL: 未配置")
    
    print(f"\nTaoSync配置：")
    print(f"  启用: {taosync_config.get('enabled')}")
    print(f"  URL: {taosync_config.get('url')}")
    print(f"  任务ID: {taosync_config.get('job_id')}")
    print()
    
    # 创建通知器
    notifier = Notifier(config)
    
    # 测试发送通知
    print("📢 测试发送ServerChan通知...")
    success = notifier.notify_info(
        "TaoSync测试",
        "这是一条测试通知\n\n任务ID: [1, 2, 3]\n状态: 测试成功"
    )
    
    if success:
        print("✅ 通知发送成功！请检查手机是否收到推送")
    else:
        print("❌ 通知发送失败")
    
    print()
    
    # 创建TaoSync客户端
    print("🔧 创建TaoSync客户端...")
    job_id_config = taosync_config.get('job_id')
    if isinstance(job_id_config, list):
        job_ids = job_id_config
    else:
        job_ids = [job_id_config] if job_id_config else [1]
    
    client = TaoSyncClient(
        url=taosync_config.get('url'),
        username=taosync_config.get('username'),
        password=taosync_config.get('password'),
        job_ids=job_ids
    )
    
    # 登录
    print("🔐 登录TaoSync...")
    if not client.login():
        print("❌ 登录失败")
        return
    
    print("✅ 登录成功\n")
    
    # 触发任务（带通知回调）
    print("🚀 触发TaoSync任务...")
    print("-" * 60)
    
    # 使用notifier的notify_info方法作为回调
    def notify_callback(msg):
        print(f"📢 [回调通知] {msg}")
        notifier.notify_info("TaoSync队列", msg)
    
    success, message = client.trigger_sync(
        check_status=False,
        notifier=notify_callback
    )
    
    print("-" * 60)
    print(f"\n触发结果:")
    print(f"  状态: {'✅ 成功' if success else '❌ 失败'}")
    print(f"  详情: {message}")
    print()
    
    if success:
        print("✅ 测试完成！请检查手机是否收到以下通知：")
        print("   1. TaoSync测试通知")
        print("   2. 每个任务的触发通知")
        print("   3. TaoSync触发完成汇总通知")
    else:
        print("⚠️  触发失败，可能没有发送通知")


if __name__ == "__main__":
    test_serverchan()
