#!/usr/bin/env python3
"""
TaoSync多任务ID触发测试脚本

测试功能：
1. 支持多个任务ID
2. 每个任务都会被触发
3. 触发过程中发送通知
4. 返回详细的触发结果

使用方法：
python test_taosync_multi_jobs.py
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.utils.taosync import TaoSyncClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def notification_callback(message: str):
    """通知回调函数"""
    print(f"📢 [通知] {message}")


def test_multi_jobs():
    """测试多任务ID触发"""
    print("=" * 60)
    print("TaoSync多任务ID触发测试")
    print("=" * 60)
    
    # ========== 配置区域 ==========
    # 从config.yaml读取的实际配置
    TAOSYNC_URL = "http://10.10.10.17:8023"
    USERNAME = "admin"
    PASSWORD = "a123456!@"
    
    # 测试多个任务ID
    JOB_IDS = [1, 2, 3]
    # ==============================
    
    print(f"\n配置信息：")
    print(f"  URL: {TAOSYNC_URL}")
    print(f"  用户名: {USERNAME}")
    print(f"  任务ID: {JOB_IDS}")
    print()
    
    # 创建客户端（支持多个任务ID）
    print("🔧 创建TaoSync客户端...")
    client = TaoSyncClient(
        url=TAOSYNC_URL,
        username=USERNAME,
        password=PASSWORD,
        job_ids=JOB_IDS  # 传入多个任务ID
    )
    
    # 登录
    print("🔐 登录TaoSync...")
    if not client.login():
        print("❌ 登录失败！")
        return
    
    print("✅ 登录成功！\n")
    
    # 触发同步（会触发所有任务ID）
    print(f"🚀 触发同步任务（共 {len(JOB_IDS)} 个任务）...")
    print("-" * 60)
    
    success, message = client.trigger_sync(
        check_status=False,  # 不检查状态，直接触发
        notifier=notification_callback  # 传入通知回调
    )
    
    print("-" * 60)
    print(f"\n触发结果：")
    print(f"  状态: {'✅ 成功' if success else '❌ 失败'}")
    print(f"  详情: {message}")
    print()
    
    return success


def test_single_job():
    """测试单个任务ID（向后兼容）"""
    print("=" * 60)
    print("TaoSync单任务ID触发测试（向后兼容）")
    print("=" * 60)
    
    TAOSYNC_URL = "http://10.10.10.17:8023"
    USERNAME = "admin"
    PASSWORD = "你的密码"
    JOB_ID = 1  # 单个任务ID
    
    print(f"\n配置信息：")
    print(f"  URL: {TAOSYNC_URL}")
    print(f"  用户名: {USERNAME}")
    print(f"  任务ID: {JOB_ID}")
    print()
    
    # 使用旧的job_id参数（向后兼容）
    client = TaoSyncClient(
        url=TAOSYNC_URL,
        username=USERNAME,
        password=PASSWORD,
        job_id=JOB_ID
    )
    
    if not client.login():
        print("❌ 登录失败！")
        return
    
    print("✅ 登录成功！\n")
    
    print("🚀 触发同步任务...")
    success, message = client.trigger_sync(notifier=notification_callback)
    
    print(f"\n触发结果：")
    print(f"  状态: {'✅ 成功' if success else '❌ 失败'}")
    print(f"  详情: {message}")
    print()
    
    return success


if __name__ == "__main__":
    print("\n请选择测试模式：")
    print("1. 多任务ID测试")
    print("2. 单任务ID测试（向后兼容）")
    
    choice = input("\n请输入选择 (1/2): ").strip()
    
    if choice == "1":
        test_multi_jobs()
    elif choice == "2":
        test_single_job()
    else:
        print("❌ 无效选择")
    
    print("\n测试完成！")
